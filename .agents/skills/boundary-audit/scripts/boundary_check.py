#!/usr/bin/env python3
"""
Boundary Audit & Checkout Working-Tree Hygiene Scanner.
Enforces CARD-294 / CARD-382 invariants:
1. No stray runtime files (*.db, live packs, wiki folders) in git working tree.
2. No un-resolved relative 'data/' storage paths in production code.
"""

import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
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


def check_working_tree_files(repo_root: Path) -> list[str]:
    violations = []

    # 1. Check for stray wiki directories in repo root
    stray_dirs = ["00_Inbox", "01_Notes", "02_Articles", "03_Archive", "04_Tasks", "05_Resources"]
    for d in stray_dirs:
        p = repo_root / d
        if p.exists():
            violations.append(f"Stray wiki directory found in repo root: {p} (must live in %LOCALAPPDATA%\\AutoReiv\\wiki\\)")

    # 2. Check for live packs directory in repo root (platform-packs/ is factory seed; packs/ is live runtime)
    live_packs = repo_root / "packs"
    if live_packs.exists():
        violations.append(f"Live packs/ directory found in repo root: {live_packs} (must live in user data directory)")

    # 3. Check for stray database files in checkout outside scratch/ and tests/
    ignored_parts = {"scratch", "tests", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".git", "test-results"}
    for db_path in repo_root.rglob("*.db"):
        rel = db_path.relative_to(repo_root)
        parts = set(rel.parts)
        if parts & ignored_parts:
            continue
        violations.append(f"Stray runtime database in working tree: {rel} (must live in user data directory)")

    return violations


def check_code_path_defaults(repo_root: Path) -> list[str]:
    violations = []
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return violations

    # Pattern catching default relative data paths e.g. root_dir: str = "data/..." or Path("data/...")
    pattern = re.compile(r'["\']data/(wiki|packs|storage|memory)["\']')

    for py_file in src_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            if pattern.search(line) and not line.strip().startswith("#"):
                # Whitelist resolver defaults or explicit comments if present
                if "resolver" in py_file.name:
                    continue
                violations.append(
                    f"{py_file.relative_to(repo_root)}:{i} - Hardcoded relative path: {line.strip()}"
                )

    return violations


def main() -> int:
    root = get_repo_root()
    print("=" * 65)
    print(" 🛡️ AutoReiv Boundary Audit (Checkout Hygiene)")
    print(f"    Target: {root}")
    print("=" * 65)

    file_violations = check_working_tree_files(root)
    code_violations = check_code_path_defaults(root)

    if file_violations:
        print("\n❌ Working Tree Violations:")
        for v in file_violations:
            print(f"   - {v}")

    if code_violations:
        print("\n⚠️ Relative Code Path Violations (need DataDirResolver):")
        for v in code_violations:
            print(f"   - {v}")

    if not file_violations and not code_violations:
        print("\n✅ Working tree is clean! Zero runtime leaks or rogue relative data paths.")
        return 0
    else:
        print(f"\n⛔ Boundary audit failed with {len(file_violations)} file leak(s) and {len(code_violations)} code path warning(s).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
