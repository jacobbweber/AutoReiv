#!/usr/bin/env python3
"""
Unified Pre-Flight Gate & Definition of Done Runner [REQ-SMK-004].
Executes all static, unit, integration, browser smoke, and RTM gates in sequence.
"""

import subprocess
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
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


def run_stage(name: str, cmd: list[str], cwd: Path) -> bool:
    print("\n============================================================")
    print(f" ▶️  Running Gate: {name}")
    print(f"    Command: {' '.join(cmd)}")
    print("============================================================")
    start_time = time.time()

    # Run command with inherited stdio
    res = subprocess.run(cmd, cwd=str(cwd), shell=(sys.platform == "win32"))
    duration = time.time() - start_time

    if res.returncode == 0:
        print(f" ✅ {name} passed ({duration:.2f}s)")
        return True
    else:
        print(f" ❌ {name} failed with exit code {res.returncode} ({duration:.2f}s)")
        return False


def main() -> int:
    root = get_repo_root()
    print("\n" + "=" * 65)
    print(" 🚀 AutoReiv Unified Pre-Flight Gate Verification")
    print(f"    Target: {root}")
    print("=" * 65)

    stages = [
        ("Python Linter (Ruff)", ["ruff", "check", "."]),
        ("Python Test Suite (Pytest)", ["pytest", "-q"]),
        ("Frontend Linter (ESLint)", ["npm", "run", "lint:frontend"]),
        ("Frontend Unit Tests (Vitest)", ["npm", "run", "test:unit:frontend"]),
        ("Playwright Multi-Studio Smoke Suite", ["npm", "run", "test:smoke"]),
        ("Requirements Traceability Matrix (RTM)", ["python", ".agents/skills/rtm-sync/scripts/verify_rtm.py"]),
    ]


    results = []
    for name, cmd in stages:
        success = run_stage(name, cmd, root)
        results.append((name, success))
        if not success:
            print(f"\n⛔ Pre-flight pipeline aborted on failed stage: {name}")
            break

    print("\n" + "=" * 65)
    print(" 📊 Pre-Flight Gate Summary")
    print("=" * 65)
    all_passed = True
    for name, success in results:
        status_icon = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status_icon:<10} | {name}")
        if not success:
            all_passed = False

    if all_passed and len(results) == len(stages):
        print("\n🎉 ALL GATES PASSED! Ready for QA merge and release handoff.")
        return 0
    else:
        print("\n❌ PRE-FLIGHT VERIFICATION FAILED. Please resolve the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
