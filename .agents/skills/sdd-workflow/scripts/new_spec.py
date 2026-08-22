#!/usr/bin/env python3
"""
Deterministic Specification Scaffolder for AWS Kiro-style SDD.
Generates requirements.md, design.md, and tasks.md from templates with zero boilerplate hallucination.
"""

import argparse
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


def derive_domain_tag(slug: str) -> str:
    words = slug.replace("_", "-").split("-")
    first_word = words[0].upper()
    return first_word[:4] if len(first_word) >= 3 else "FEAT"


def main():
    parser = argparse.ArgumentParser(description="Create a new 3-file EARS specification from template")
    parser.add_argument("feature_name", help="Name of the feature (e.g. 'user-authentication' or 'payment-gateway')")
    parser.add_argument("--domain", help="Requirement domain tag (e.g. 'AUTH', 'PAY'). Defaults to first word of feature.")
    args = parser.parse_args()

    repo_root = get_repo_root()
    slug = sanitize_slug(args.feature_name)
    title = slug.replace("-", " ").replace("_", " ").title()
    domain_tag = (args.domain.upper() if args.domain else derive_domain_tag(slug))

    template_dir = repo_root / "docs" / "specs" / "_template"
    target_dir = repo_root / "docs" / "specs" / slug

    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}", file=sys.stderr)
        sys.exit(1)

    if target_dir.exists():
        print(f"❌ Target spec directory already exists: {target_dir}", file=sys.stderr)
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    template_files = ["requirements.md", "design.md", "tasks.md"]
    created_files = []

    for filename in template_files:
        src = template_dir / filename
        dst = target_dir / filename
        if not src.exists():
            print(f"⚠️ Warning: Missing template file {src}", file=sys.stderr)
            continue

        content = src.read_text(encoding="utf-8")
        content = content.replace("[Feature Name]", title)
        content = content.replace("REQ-DOMAIN-", f"REQ-{domain_tag}-")
        dst.write_text(content, encoding="utf-8")
        created_files.append(dst.relative_to(repo_root).as_posix())

    print(f"✅ Created 3-file specification for '{title}' under docs/specs/{slug}/:")
    for f in created_files:
        print(f"   📄 {f}")
    print(f"\n💡 Next Step: Edit requirements.md with Socratic requirements in EARS format (tag: [REQ-{domain_tag}-xxx]).")


if __name__ == "__main__":
    main()
