#!/usr/bin/env python3
"""List AutoReiv work card statuses from docs/cards/CARD-*.md."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STATUS_BQ = re.compile(r">\s*\*\*Status\*\*:\s*(.+)", re.IGNORECASE)
STATUS_YAML = re.compile(r"^status:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
TITLE_H1 = re.compile(r"^#\s+\[?(CARD-\d+)\]?\s*(.*)$", re.MULTILINE)
BRANCH_BQ = re.compile(r">\s*\*\*Branch\*\*:\s*(.+)", re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def parse_card(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    # first ~40 lines usually hold header
    head = "\n".join(text.splitlines()[:60])
    status = None
    m = STATUS_BQ.search(head)
    if m:
        status = m.group(1).strip().strip("*").strip()
    else:
        m = STATUS_YAML.search(head)
        if m:
            status = m.group(1).strip().strip("\"'")
    tm = TITLE_H1.search(head)
    card_id = path.stem.split("-")[0] + "-" + path.stem.split("-")[1] if path.stem.startswith("CARD-") else path.stem
    # better id from filename CARD-294-...
    parts = path.stem.split("-")
    if len(parts) >= 2 and parts[0] == "CARD":
        card_id = f"{parts[0]}-{parts[1]}"
        title_rest = "-".join(parts[2:]) if len(parts) > 2 else ""
    else:
        title_rest = path.stem
    if tm:
        card_id = tm.group(1)
        title_rest = tm.group(2).strip() or title_rest
    branch = None
    bm = BRANCH_BQ.search(head)
    if bm:
        branch = bm.group(1).strip().strip("`")
    return {
        "id": card_id,
        "title": title_rest.replace("-", " ").strip() or path.stem,
        "status": status or "UNKNOWN",
        "branch": branch or "",
        "path": str(path.relative_to(repo_root())).replace("\\", "/"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="List CARD statuses under docs/cards/")
    parser.add_argument("--status", help="Filter by status substring (case-insensitive)")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--cards-dir",
        type=Path,
        default=None,
        help="Override cards directory (default: <repo>/docs/cards)",
    )
    args = parser.parse_args()
    cards_dir = args.cards_dir or (repo_root() / "docs" / "cards")
    files = sorted(cards_dir.glob("CARD-*.md"))
    rows = [parse_card(p) for p in files]
    if args.status:
        needle = args.status.lower()
        rows = [r for r in rows if needle in r["status"].lower()]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    # summary counts
    from collections import Counter

    counts = Counter(r["status"] for r in rows)
    def out(s: str) -> None:
        try:
            print(s)
        except UnicodeEncodeError:
            print(s.encode("ascii", "replace").decode("ascii"))

    out(f"cards={len(rows)} dir={cards_dir}")
    out("status_counts=" + ", ".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))))
    out("")
    out(f"{'ID':<12} {'STATUS':<28} {'TITLE'}")
    out("-" * 100)
    for r in rows:
        title = r["title"][:60]
        out(f"{r['id']:<12} {r['status'][:28]:<28} {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
