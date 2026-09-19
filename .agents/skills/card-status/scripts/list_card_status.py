#!/usr/bin/env python3
"""
AutoReiv / SDLC Skill: list_card_status.py
Granular, token-efficient work card query and inspection tool.
Parses docs/cards/CARD-*.md supporting both YAML frontmatter and Markdown blockquotes.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, List

try:
    import yaml
except ImportError:
    yaml = None

STATUS_BQ = re.compile(r">\s*\*\*Status\*\*:\s*(.+)", re.IGNORECASE)
CREATED_BQ = re.compile(r">\s*\*\*Created\*\*:\s*(.+)", re.IGNORECASE)
COMPLETED_BQ = re.compile(r">\s*\*\*Completed\*\*:\s*(.+)", re.IGNORECASE)
ADR_BQ = re.compile(r">\s*\*\*ADR(?: Reference)?\*\*:\s*(.+)", re.IGNORECASE)
LABELS_BQ = re.compile(r">\s*\*\*Labels\*\*:\s*(.+)", re.IGNORECASE)
BRANCH_BQ = re.compile(r">\s*\*\*Branch\*\*:\s*(.+)", re.IGNORECASE)
TITLE_H1 = re.compile(r"^#\s+\[?(CARD-\d+)\]?\s*(.*)$", re.MULTILINE)
INTENT_SECTION = re.compile(r"##\s+(?:1\.\s+)?(?:Why|Intent|Goal)[^\n]*\n+([^#]+)", re.IGNORECASE)

CLOSED_KEYWORDS = {"done", "complete", "completed", "superseded", "retired", "abandoned"}
PARKED_KEYWORDS = {"parked", "holding", "deferred", "horizon"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def parse_labels(raw: Any) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip().strip("`\"'") for x in raw if str(x).strip()]
    raw_str = str(raw).strip()
    items = re.split(r"[,;]", raw_str)
    return [item.strip().strip("`\"'") for item in items if item.strip()]


def classify_status(status_str: str) -> str:
    s = (status_str or "").lower().strip()
    if any(k in s for k in CLOSED_KEYWORDS):
        return "closed"
    if any(k in s for k in PARKED_KEYWORDS):
        return "parked"
    return "open"


def parse_card(path: Path) -> dict:
    resolved_path = path.resolve()
    text = resolved_path.read_text(encoding="utf-8", errors="replace")

    status = None
    created = None
    completed = None
    adr = None
    labels: List[str] = []
    branch = None
    title = None
    card_id = None

    # 1. Parse YAML frontmatter if present
    if text.startswith("---") and yaml is not None:
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if isinstance(fm, dict):
                    status = fm.get("status")
                    created = fm.get("created")
                    completed = fm.get("completed")
                    adr = fm.get("adr") or fm.get("adr_reference")
                    labels = parse_labels(fm.get("labels") or fm.get("tags"))
                    branch = fm.get("branch")
                    card_id = fm.get("id")
                    title = fm.get("title")
            except Exception:
                pass

    # 2. Parse Markdown blockquote headers in first ~80 lines
    head = "\n".join(text.splitlines()[:80])

    if not status:
        m = STATUS_BQ.search(head)
        if m:
            status = m.group(1).strip().strip("*").strip()
    if not created:
        m = CREATED_BQ.search(head)
        if m:
            created = m.group(1).strip().strip("*").strip()
    if not completed:
        m = COMPLETED_BQ.search(head)
        if m:
            completed = m.group(1).strip().strip("*").strip()
    if not adr:
        m = ADR_BQ.search(head)
        if m:
            adr = m.group(1).strip().strip("*").strip()
    if not labels:
        m = LABELS_BQ.search(head)
        if m:
            labels = parse_labels(m.group(1))
    if not branch:
        m = BRANCH_BQ.search(head)
        if m:
            branch = m.group(1).strip().strip("`")

    # 3. Parse Title & ID from H1
    tm = TITLE_H1.search(head)
    if tm:
        card_id = card_id or tm.group(1)
        parsed_title = tm.group(2).strip().strip("- ")
        title = title or parsed_title

    # 4. Fallback ID and Title from filename (CARD-xxx-slug.md)
    stem_parts = path.stem.split("-")
    if len(stem_parts) >= 2 and stem_parts[0] == "CARD":
        fallback_id = f"{stem_parts[0]}-{stem_parts[1]}"
        fallback_title = "-".join(stem_parts[2:]).replace("-", " ").strip()
    else:
        fallback_id = path.stem
        fallback_title = path.stem

    card_id = card_id or fallback_id
    title = title or fallback_title

    # Numeric value for clean numerical sorting
    num_match = re.search(r"CARD-(\d+)", card_id)
    card_number = int(num_match.group(1)) if num_match else 0

    # 5. Extract Intent / Why section excerpt
    intent_match = INTENT_SECTION.search(text)
    intent_text = ""
    if intent_match:
        lines = [line.strip() for line in intent_match.group(1).strip().splitlines() if line.strip()]
        intent_text = " ".join(lines[:3])[:300]

    category = classify_status(status or "Unknown")

    try:
        rel_path = str(resolved_path.relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        rel_path = str(resolved_path)

    return {
        "id": card_id,
        "number": card_number,
        "title": title,
        "status": status or "UNKNOWN",
        "category": category,
        "created": str(created) if created else None,
        "completed": str(completed) if completed else None,
        "adr": str(adr) if adr else None,
        "labels": labels,
        "branch": branch,
        "intent": intent_text,
        "path": rel_path,
    }


def search_matches(row: dict, query: str) -> bool:
    q = query.lower()
    if q in row["id"].lower():
        return True
    if q in row["title"].lower():
        return True
    if any(q in lbl.lower() for lbl in row["labels"]):
        return True
    if row["adr"] and q in row["adr"].lower():
        return True
    if row["intent"] and q in row["intent"].lower():
        return True
    return False


def print_card_detail(card: dict) -> None:
    print("=" * 80)
    print(f" [{card['id']}] {card['title']}")
    print("=" * 80)
    print(f"  Status:       {card['status']} ({card['category']})")
    print(f"  Created:      {card['created'] or 'N/A'}")
    if card["completed"]:
        print(f"  Completed:    {card['completed']}")
    if card["branch"]:
        print(f"  Branch:       {card['branch']}")
    if card["adr"]:
        print(f"  ADR:          {card['adr']}")
    labels_str = ", ".join(card["labels"]) if card["labels"] else "none"
    print(f"  Labels:       {labels_str}")
    print(f"  File:         {card['path']}")
    if card["intent"]:
        print("\n  Intent / Why (Beat 1):")
        print(f"  {card['intent']}")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AutoReiv Work Card Status & Search Board (docs/cards/CARD-*.md)"
    )
    # Scope filters
    scope_group = parser.add_argument_group("Scope Filters")
    scope_group.add_argument(
        "--all",
        action="store_true",
        help="Show all cards including closed/done (default is active/open cards only)",
    )
    scope_group.add_argument(
        "--open",
        "--active",
        action="store_true",
        help="Show only active/open cards (Ready, In Review, In Progress) [Default]",
    )
    scope_group.add_argument(
        "--done",
        "--closed",
        action="store_true",
        help="Show only completed/closed cards",
    )
    scope_group.add_argument(
        "--parked",
        action="store_true",
        help="Show parked/holding cards",
    )

    # Search & Inspection filters
    filter_group = parser.add_argument_group("Granular Search & Inspection")
    filter_group.add_argument(
        "--card",
        "--id",
        dest="card_id",
        help="Inspect a single card in detail (e.g. 382 or CARD-382)",
    )
    filter_group.add_argument(
        "-q",
        "--search",
        help="Search across ID, title, labels, ADR, and intent excerpt (case-insensitive)",
    )
    filter_group.add_argument(
        "--label",
        "--tag",
        help="Filter by label or tag substring (e.g. 'type:bug', 'wiki', 'chat')",
    )
    filter_group.add_argument(
        "--status",
        help="Filter by status substring (e.g. 'Ready', 'In Review', 'Parked')",
    )
    filter_group.add_argument(
        "--recent",
        "--latest",
        nargs="?",
        const=10,
        type=int,
        metavar="N",
        help="Show the N latest cards sorted by card number descending (default: 10)",
    )
    filter_group.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit number of displayed table rows",
    )

    # Output format
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON array of cards instead of human table",
    )
    parser.add_argument(
        "--cards-dir",
        type=Path,
        default=None,
        help="Override cards directory (default: <repo>/docs/cards)",
    )

    args = parser.parse_args()

    cards_dir = (args.cards_dir or (repo_root() / "docs" / "cards")).resolve()
    if not cards_dir.is_dir():
        print(f"❌ Error: Cards directory not found: {cards_dir}")
        return 1

    files = sorted(cards_dir.glob("CARD-*.md"))
    all_cards = [parse_card(p) for p in files]
    all_cards.sort(key=lambda c: c["number"])

    # 1. Single-card detail view
    if args.card_id:
        target = args.card_id.strip().upper()
        if not target.startswith("CARD-") and target.isdigit():
            target = f"CARD-{int(target):03d}"
        match = next(
            (c for c in all_cards if c["id"] == target or target in c["id"] or target in c["path"].upper()),
            None,
        )
        if not match:
            print(f"❌ Error: Card '{args.card_id}' not found under {cards_dir.relative_to(repo_root())}")
            return 1
        if args.json:
            print(json.dumps(match, indent=2))
        else:
            print_card_detail(match)
        return 0

    # 2. Status categorization counts
    cat_counts = Counter(c["category"] for c in all_cards)
    open_count = cat_counts.get("open", 0)
    done_count = cat_counts.get("closed", 0)
    parked_count = cat_counts.get("parked", 0)
    total_count = len(all_cards)

    # Determine default filtering:
    # If explicit filters (--all, --done, --parked, --status, --recent, --search, --label) were NOT passed, default to open cards.
    has_explicit_filter = any(
        [
            args.all,
            args.open,
            args.done,
            args.parked,
            args.status,
            args.recent is not None,
            args.search,
            args.label,
        ]
    )

    rows = list(all_cards)

    if not has_explicit_filter or args.open:
        filter_label = "active/open cards"
        rows = [r for r in rows if r["category"] == "open"]
    elif args.done:
        filter_label = "completed/closed cards"
        rows = [r for r in rows if r["category"] == "closed"]
    elif args.parked:
        filter_label = "parked cards"
        rows = [r for r in rows if r["category"] == "parked"]
    else:
        filter_label = "all cards"

    # Secondary granular filters
    if args.status:
        needle = args.status.lower()
        rows = [r for r in rows if needle in r["status"].lower()]
        filter_label += f" matching status '{args.status}'"

    if args.label:
        needle = args.label.lower()
        rows = [r for r in rows if any(needle in lbl.lower() for lbl in r["labels"])]
        filter_label += f" matching label '{args.label}'"

    if args.search:
        rows = [r for r in rows if search_matches(r, args.search)]
        filter_label += f" matching search '{args.search}'"

    # Sort & Limit
    if args.recent is not None:
        rows = sorted(rows, key=lambda r: r["number"], reverse=True)[: args.recent]
        filter_label += f" (latest {args.recent})"
    elif args.limit:
        rows = rows[: args.limit]
        filter_label += f" (limit {args.limit})"

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    # Terminal output
    def out(s: str) -> None:
        try:
            print(s)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode("ascii"))

    out(
        f"AutoReiv Card Status Board (Total: {total_count} | Open: {open_count} | Done: {done_count} | Parked: {parked_count})"
    )
    out(f"Showing {len(rows)} {filter_label}:")
    out("")

    if not rows:
        out("  (No cards match the current filter criteria)")
        return 0

    out(f"{'ID':<10} {'STATUS':<14} {'LABELS':<28} {'TITLE'}")
    out("-" * 96)
    for r in rows:
        labels_preview = ", ".join(r["labels"])[:26]
        title_preview = r["title"][:42]
        status_preview = r["status"][:13]
        out(f"{r['id']:<10} {status_preview:<14} {labels_preview:<28} {title_preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
