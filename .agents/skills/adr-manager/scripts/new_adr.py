#!/usr/bin/env python3
"""
Deterministic Architecture Decision Record (ADR) Scaffolder.
Finds next sequential number and initializes new ADR from template.
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

# Ensure safe UTF-8 output
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / ".git").exists() or (current / "AGENTS.md").exists():
            return current
        current = current.parent
    return Path.cwd()


def sanitize_slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-")
    return re.sub(r"-+", "-", slug)


def get_next_adr_number(adr_dir: Path) -> int:
    max_num = 0
    if not adr_dir.exists():
        return 1
    for f in adr_dir.glob("*.md"):
        match = re.match(r"^(\d{4})-", f.name)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return max_num + 1


def main():
    parser = argparse.ArgumentParser(description="Create a new ADR from template")
    parser.add_argument(
        "title", help="Title of the architecture decision (e.g. 'Use Redis for Session Storage')"
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    adr_dir = repo_root / "docs" / "adr"
    template_file = adr_dir / "0000-template.md"

    if not template_file.exists():
        print(f"❌ Template file not found: {template_file}", file=sys.stderr)
        sys.exit(1)

    next_num = get_next_adr_number(adr_dir)
    num_str = f"{next_num:04d}"
    slug = sanitize_slug(args.title)
    target_filename = f"{num_str}-{slug}.md"
    target_file = adr_dir / target_filename

    today = datetime.date.today().isoformat()

    content = template_file.read_text(encoding="utf-8")
    content = content.replace(
        "ADR-0000: [Short Title of the Decision]", f"ADR-{num_str}: {args.title}"
    )
    content = content.replace("YYYY-MM-DD", today)

    target_file.write_text(content, encoding="utf-8")

    rel_path = target_file.relative_to(repo_root).as_posix()
    print(f"✅ Created ADR-{num_str}: '{args.title}'")
    print(f"   📄 {rel_path}")
    print(
        f"\n💡 Next Step: Edit {rel_path} to record Context, Considered Options, and Decision Outcome."
    )


if __name__ == "__main__":
    main()
