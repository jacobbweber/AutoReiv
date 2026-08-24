#!/usr/bin/env python3
"""
AutoReiv / SDLC Intake Script: new_card.py
Scaffolds a new ready-to-build work card under .github/cards/
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
    parser.add_argument("--spec", default="none", help="Spec or ADR reference")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    cards_dir = repo_root / ".github" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    card_num = get_next_card_number(cards_dir)
    card_id = f"CARD-{card_num:03d}"
    slug = slugify(args.title)
    filename = f"{card_id}-{slug}.md"
    target_file = cards_dir / filename

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    card_content = f"""# [{card_id}] {args.title}

> **Status**: Ready
> **Created**: {now_iso}
> **Spec Reference**: {args.spec}
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
{args.intent or "Describe the core motivation and value. What is the human visionary trying to achieve, and why?"}

---

## 2. What to Build
{args.what or "Concrete description of the change. List endpoints, files, and UI elements involved."}

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
"""

    target_file.write_text(card_content, encoding="utf-8")
    print(f"\n✅ Successfully created work card: {target_file.relative_to(repo_root)}")
    print(f"📄 Card ID: {card_id}")
    print(
        "💡 Next Step: Review and refine the acceptance criteria with the human visionary before drafting the spec!\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
