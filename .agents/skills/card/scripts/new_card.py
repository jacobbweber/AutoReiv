#!/usr/bin/env python3
"""Create a card from the bug or feature template (CARD-559).

    python .agents/skills/card/scripts/new_card.py "<title>" --type bug --priority P2 --milestone M22 [--slug short-name]

Writes docs/cards/CARD-<next>-<slug>.md from .agents/skills/card/templates/<type>.md.
Dedupe first: list_card_status.py --open --search "<keyword>" and rg docs/findings.md.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def slugify(text: str, words: int = 6) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    parts = [p for p in re.split(r"[\s_-]+", text) if p]
    return "-".join(parts[:words])


def get_next_card_number(cards_dir: Path) -> int:
    numbers = [int(m.group(1)) for c in cards_dir.glob("CARD-*.md") if (m := re.match(r"CARD-(\d+)", c.name))]
    return max(numbers, default=0) + 1


def render(template: str, card_id: str, title: str, slug: str, priority: str, milestone: str, today: str) -> str:
    num = card_id.split("-")[1]
    out = template.replace("CARD-N", card_id).replace("card-N-slug", f"card-{num}-{slug}").replace("card-N", f"card-{num}")
    out = out.replace("YYYY-MM-DD", today).replace("priority: P2", f"priority: {priority}").replace("milestone: M22", f"milestone: {milestone}")
    out = re.sub(r'^title: ".*"$', f'title: "{title}"', out, count=1, flags=re.M)
    out = re.sub(r"^# CARD-\d+ <title>$", f"# {card_id} {title}", out, count=1, flags=re.M)
    return out


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Create a card from the bug or feature template.")
    p.add_argument("title")
    p.add_argument("--type", choices=("bug", "feature"), default="bug")
    p.add_argument("--priority", choices=("P0", "P1", "P2", "P3"), default="P2")
    p.add_argument("--milestone", default="M22")
    p.add_argument("--slug", default="")
    p.add_argument("--cards-dir", default=str(ROOT / "docs" / "cards"))
    a = p.parse_args(argv)
    cards_dir = Path(a.cards_dir)
    cards_dir.mkdir(parents=True, exist_ok=True)
    card_id = f"CARD-{get_next_card_number(cards_dir)}"
    slug = slugify(a.slug or a.title)
    target = cards_dir / f"{card_id}-{slug}.md"
    text = render((TEMPLATES / f"{a.type}.md").read_text(encoding="utf-8"), card_id, a.title, slug, a.priority, a.milestone, date.today().isoformat())
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"Created {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
    print("Fill every section and the proof: front matter. If needs_decision is not none, send the plan and wait for build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
