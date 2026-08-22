#!/usr/bin/env python3
"""
Requirements Traceability Matrix (RTM) Validator & Pre-Flight DoD Gate.
Ensures machine-readable requirements, specs, ADRs, source modules, and tests stay synchronized.
Supports unified pre-flight verification across tests, linters, and RTM checks.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure safe UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_repo_root() -> Path:
    """Find repository root by looking for .git or AGENTS.md."""
    current = Path(__file__).resolve().parent
    while current.parent != current:
        if (current / ".git").exists() or (current / "AGENTS.md").exists():
            return current
        current = current.parent
    return Path.cwd()


def load_json(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_rtm_structure(data: Dict[str, Any]) -> List[str]:
    """Basic schema and consistency validator."""
    errors = []
    required_top = ["version", "project", "requirements"]
    for field in required_top:
        if field not in data:
            errors.append(f"Missing top-level field: '{field}'")

    if not isinstance(data.get("requirements", []), list):
        errors.append("'requirements' must be a list.")
        return errors

    seen_ids: Set[str] = set()
    req_fields = ["id", "title", "status", "spec", "source_modules", "test_suites"]

    for idx, req in enumerate(data.get("requirements", [])):
        if not isinstance(req, dict):
            errors.append(f"Requirement at index {idx} must be an object.")
            continue

        req_id = req.get("id", f"<index {idx}>")
        for field in req_fields:
            if field not in req:
                errors.append(f"Requirement '{req_id}' is missing required field: '{field}'")

        if req_id in seen_ids:
            errors.append(f"Duplicate Requirement ID: '{req_id}'")
        seen_ids.add(req_id)

    return errors


def verify_file_existence(repo_root: Path, data: Dict[str, Any]) -> List[str]:
    """Verify that all referenced paths exist in the workspace."""
    errors = []
    for req in data.get("requirements", []):
        req_id = req.get("id", "UNKNOWN")

        # Check spec file
        spec_path = req.get("spec")
        if spec_path and not (repo_root / spec_path).exists():
            errors.append(f"[{req_id}] Spec file does not exist: {spec_path}")

        # Check ADR file if specified
        adr_path = req.get("adr")
        if adr_path and not (repo_root / adr_path).exists():
            errors.append(f"[{req_id}] ADR file does not exist: {adr_path}")

        # Check source modules
        for src in req.get("source_modules", []):
            if not (repo_root / src).exists():
                errors.append(f"[{req_id}] Source module does not exist: {src}")

        # Check test suites
        for test in req.get("test_suites", []):
            if not (repo_root / test).exists():
                errors.append(f"[{req_id}] Test suite does not exist: {test}")

    return errors


def calculate_blast_radius(repo_root: Path, data: Dict[str, Any], target_file: str) -> None:
    """Calculate blast radius and impacted components for a given file."""
    norm_target = str(Path(target_file).as_posix()).lstrip("./")
    matched_reqs = []

    for req in data.get("requirements", []):
        spec = str(Path(req.get("spec", "")).as_posix()).lstrip("./")
        adr = str(Path(req.get("adr", "") or "").as_posix()).lstrip("./")
        sources = [str(Path(s).as_posix()).lstrip("./") for s in req.get("source_modules", [])]
        tests = [str(Path(t).as_posix()).lstrip("./") for t in req.get("test_suites", [])]

        if norm_target in [spec, adr] or norm_target in sources or norm_target in tests:
            matched_reqs.append(req)

    print(f"\n🎯 Blast Radius Analysis for: {norm_target}")
    print("=" * 70)
    if not matched_reqs:
        print("  No direct requirement mapping found in rtm.json.")
        print("  💡 Tip: Register this file in docs/rtm.json under its corresponding [REQ-xxx].")
        print("=" * 70 + "\n")
        return

    for req in matched_reqs:
        print(f"\n📌 Requirement: {req.get('id')} - {req.get('title')}")
        print(f"   Status     : {req.get('status')}")
        print(f"   Spec File  : {req.get('spec')}")
        if req.get("adr"):
            print(f"   ADR        : {req.get('adr')}")
        if req.get("c4_component"):
            print(f"   Component  : {req.get('c4_component')}")
        print("   Linked Sources:")
        for s in req.get("source_modules", []):
            print(f"     - {s}")
        print("   Test Suites to Execute:")
        for t in req.get("test_suites", []):
            print(f"     👉 {t}")
    print("=" * 70 + "\n")


def print_summary(data: Dict[str, Any]) -> None:
    reqs = data.get("requirements", [])
    print(f"\n📊 Requirements Traceability Summary ({data.get('project')})")
    print("=" * 75)
    print(f"{'ID':<16} | {'Status':<12} | {'Component':<18} | {'Title'}")
    print("-" * 75)
    for req in reqs:
        comp = req.get("c4_component") or "N/A"
        print(
            f"{req.get('id', ''):<16} | {req.get('status', ''):<12} | {comp:<18} | {req.get('title', '')[:25]}"
        )
    print("=" * 75)
    if len(reqs) == 0:
        print("Total Requirements Tracked: 0 (Ready for your first feature spec in docs/specs/)\n")
    else:
        print(f"Total Requirements Tracked: {len(reqs)}\n")


def parse_commands_from_tech_steering(repo_root: Path) -> Dict[str, str]:
    """Parse test and lint commands from steering/tech.md."""
    tech_path = repo_root / "steering" / "tech.md"
    commands = {}
    if not tech_path.exists():
        return commands

    content = tech_path.read_text(encoding="utf-8")
    for line in content.splitlines():
        match = re.match(r"^([a-zA-Z0-9_]+_cmd):\s*(.+)$", line.strip())
        if match:
            commands[match.group(1)] = match.group(2).strip()
    return commands


def run_command(cmd: str, repo_root: Path) -> Tuple[bool, str, float]:
    start = time.time()
    try:
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        duration = time.time() - start
        output = res.stdout if res.returncode == 0 else (res.stderr or res.stdout)
        return (res.returncode == 0, output.strip(), duration)
    except Exception as e:
        return (False, str(e), time.time() - start)


def run_pre_flight_check(repo_root: Path, rtm_path: Path) -> bool:
    """Execute complete unified Definition of Done gate."""
    print("\n" + "=" * 70)
    print("🚦 RUNNING DEFINITION OF DONE (DoD) PRE-FLIGHT VERIFICATION")
    print("=" * 70)

    overall_pass = True

    # 1. RTM Validation
    print("\n[1/3] Validating Requirements Traceability Matrix (RTM)...")
    try:
        data = load_json(rtm_path)
        struct_errs = validate_rtm_structure(data)
        file_errs = verify_file_existence(repo_root, data)
        all_rtm_errs = struct_errs + file_errs
        if all_rtm_errs:
            print("  ❌ RTM Check: FAILED")
            for err in all_rtm_errs:
                print(f"     • {err}")
            overall_pass = False
        else:
            print(
                f"  ✅ RTM Check: PASSED ({len(data.get('requirements', []))} requirements verified)"
            )
    except Exception as e:
        print(f"  ❌ RTM Check: ERROR ({e})")
        overall_pass = False

    # 2. Tech Steering Commands
    cmds = parse_commands_from_tech_steering(repo_root)
    test_cmd = cmds.get("test_all_cmd") or cmds.get("test_unit_cmd")
    lint_cmd = cmds.get("lint_cmd")

    # Lint Check
    print("\n[2/3] Running Code Quality & Static Analysis...")
    if lint_cmd and not lint_cmd.startswith("echo"):
        passed, out, dur = run_command(lint_cmd, repo_root)
        if passed:
            print(f"  ✅ Linter ({lint_cmd}): PASSED ({dur:.2f}s)")
        else:
            print(f"  ❌ Linter ({lint_cmd}): FAILED ({dur:.2f}s)")
            print(f"     Output: {out[:300]}")
            overall_pass = False
    else:
        print("  ℹ️ Linter: Skipped (no active command in steering/tech.md)")

    # Test Suite Check
    print("\n[3/3] Running Automated Test Suite...")
    if test_cmd and not test_cmd.startswith("echo"):
        passed, out, dur = run_command(test_cmd, repo_root)
        if passed:
            print(f"  ✅ Test Suite ({test_cmd}): PASSED ({dur:.2f}s)")
        else:
            print(f"  ❌ Test Suite ({test_cmd}): FAILED ({dur:.2f}s)")
            print(f"     Output: {out[:300]}")
            overall_pass = False
    else:
        print("  ℹ️ Test Suite: Skipped (no active command in steering/tech.md)")

    print("\n" + "=" * 70)
    if overall_pass:
        print("🎉 PRE-FLIGHT STATUS: ALL QUALITY GATES PASSED (Ready for PR)")
    else:
        print("❌ PRE-FLIGHT STATUS: FAILED (Resolve errors before opening PR)")
    print("=" * 70 + "\n")
    return overall_pass


def run_self_tests() -> bool:
    """Run internal sanity checks."""
    sample_data = {
        "version": "1.0.0",
        "project": "test-project",
        "requirements": [
            {
                "id": "REQ-TEST-001",
                "title": "Sample Test Req",
                "status": "implemented",
                "spec": "docs/specs/test.md",
                "source_modules": ["src/test.py"],
                "test_suites": ["tests/test.py"],
            }
        ],
    }
    errors = validate_rtm_structure(sample_data)
    assert not errors, f"Self-test validation failed: {errors}"
    print("✅ Self-test passed successfully.")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Requirements Traceability Matrix (RTM) Validator & DoD Gate"
    )
    parser.add_argument("--rtm", default="docs/rtm.json", help="Path to rtm.json")
    parser.add_argument("--impact", help="Calculate blast radius for a given file path")
    parser.add_argument("--summary", action="store_true", help="Display traceability summary table")
    parser.add_argument(
        "--pre-flight",
        action="store_true",
        help="Run full unified Definition of Done pre-flight check",
    )
    parser.add_argument("--test", action="store_true", help="Run internal self-tests")
    args = parser.parse_args()

    if args.test:
        run_self_tests()
        sys.exit(0)

    repo_root = get_repo_root()
    rtm_path = repo_root / args.rtm

    if args.pre_flight:
        success = run_pre_flight_check(repo_root, rtm_path)
        sys.exit(0 if success else 1)

    try:
        data = load_json(rtm_path)
    except Exception as e:
        print(f"❌ Error reading RTM at {rtm_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if args.impact:
        calculate_blast_radius(repo_root, data, args.impact)
        sys.exit(0)

    if args.summary:
        print_summary(data)
        sys.exit(0)

    # Perform full verification
    print(f"🔍 Validating {args.rtm} against workspace...")
    structural_errors = validate_rtm_structure(data)
    file_errors = verify_file_existence(repo_root, data)

    all_errors = structural_errors + file_errors
    if all_errors:
        print(f"\n❌ RTM Validation Failed with {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"   • {err}")
        sys.exit(1)
    else:
        print("✅ RTM is valid. All requirement links and references resolve correctly.")
        print_summary(data)


if __name__ == "__main__":
    main()
