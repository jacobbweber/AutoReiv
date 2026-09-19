#!/usr/bin/env python3
"""
AutoReiv / SDLC Intake Script: new_card.py
Scaffolds a new ready-to-build work card under docs/cards/
following the .github/ISSUE_TEMPLATE/card.yml standard.
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


def get_next_card_number(cards_dir: Path) -> int:
    cards_dir.mkdir(parents=True, exist_ok=True)
    existing_cards = list(cards_dir.glob("CARD-*.md"))
    if not existing_cards:
        return 1
    numbers = []
    for c in existing_cards:
        match = re.match(r"CARD-(\d+)", c.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Scaffold a new SDLC work card.")
    parser.add_argument("title", help="Concise outcome/title of the work card (e.g. 'LLM Provider Settings')")
    parser.add_argument("--intent", default="", help="Why / intent of this feature")
    parser.add_argument("--what", default="", help="What to build (endpoints, files, UI elements)")
    parser.add_argument("--adr", default="none", help="ADR reference (or 'none')")
    parser.add_argument(
        "--labels",
        default="type:feature, needs-triage",
        help="Comma-separated labels (e.g. 'type:bug, area:wiki')",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    cards_dir = repo_root / "docs" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    card_num = get_next_card_number(cards_dir)
    card_id = f"CARD-{card_num:03d}"
    slug = slugify(args.title)
    filename = f"{card_id}-{slug}.md"
    target_file = cards_dir / filename

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    raw_labels = [lbl.strip().strip("`\"'") for lbl in re.split(r"[,;]", args.labels) if lbl.strip()]
    yaml_labels = "\n".join(f"  - {lbl}" for lbl in raw_labels)
    bq_labels = ", ".join(f"`{lbl}`" for lbl in raw_labels)

    card_content = f"""---
id: {card_id}
title: "{args.title}"
status: Ready
created: {now_iso}
adr: {args.adr}
labels:
{yaml_labels}
---

# [{card_id}] {args.title}

> **Status**: Ready
> **Created**: {now_iso}
> **ADR Reference**: {args.adr}
> **Labels**: {bq_labels}

---

## 1. Why / Intent (Beat 1)

{args.intent or "Describe the core motivation and value. What is Jacob trying to achieve, and why?"}

---

## 2. What AutoReiv Does Now (Beat 2)

Describe current behavior, code paths, or architecture.

---

## 3. What Will Change (Beat 3)

{args.what or "Concrete description of the technical modifications, endpoints, files, and UI elements involved."}

---

## 4. What Dies Today (The Prune List - Beat 4)

- Explicit list of functions, variables, routes, DOM elements, or files to delete/retire.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL ...
- **Event-Driven**: WHEN ... THE SYSTEM SHALL ...
- **Negative Assertion**: Automated tests shall explicitly assert that ...

---

## 6. Constraints & Verification Plan

- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Isolated feature branch cut from `qa`.
- Unified preflight verification passes via `npm run preflight`.
"""

    target_file.write_text(card_content, encoding="utf-8")
    print(f"\n✅ Successfully created work card: {target_file.relative_to(repo_root)}")
    print(f"📄 Card ID: {card_id}")
    print(
        "💡 Next Step: Review and refine the Four Beats and acceptance criteria with Jacob before asking him to build!\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
