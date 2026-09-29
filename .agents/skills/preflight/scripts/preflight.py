#!/usr/bin/env python3
"""Preflight tiers (CARD-559, CARD-560). Run from the repo root.

    python .agents/skills/preflight/scripts/preflight.py --fast [--base qa]   # card proof, and after each merge to qa (~1 min)
    python .agents/skills/preflight/scripts/preflight.py --release            # gate before merging qa into main; the default

pytest stages run with `-n auto` when pytest-xdist is installed (serially otherwise); tests marked `serial` run in
a separate serial pass. Every stage runs (no stop on the first failure). A table is printed at the end and written
to scratch/preflight/last.md; each stage's output is in scratch/preflight/<stage>.log. Exit 0 only when every
stage passed or matched a named known failure (KNOWN_LINT).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "scratch" / "preflight"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe") if os.name == "nt" else sys.executable
if not Path(PY).exists():
    PY = sys.executable
PYTEST = [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def _has_xdist() -> bool:
    try:
        return subprocess.run([PY, "-c", "import xdist"], capture_output=True).returncode == 0
    except OSError:
        return False


# Parallel pytest (CARD-560): `-n auto` when pytest-xdist is installed; `serial` tests get their own pass.
PAR = ["-n", "auto"] if _has_xdist() else []
PYTEST_PAR = PYTEST + PAR
RUFF = [PY, "-m", "ruff", "check"]
HONESTY = [PY, ".agents/skills/preflight/scripts/honesty_smoke_skill_261.py", "--validate"]
JS_LINT_ROOTS = ("src/web/static/", "tests/unit/frontend/", "tests/e2e/")

# Named known lint failures: (card, error count). A stage at or below the count reports KNOWN, above it fails.
# Remove an entry when its card lands; a count of 0 then passes normally.
KNOWN_LINT: dict[str, tuple[str, int]] = {}  # e.g. {"ruff": ("CARD-N", 3)}; empty since CARD-454/456


def _run(cmd: list[str]) -> tuple[int, str, float]:
    t0 = time.time()
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
                         shell=(os.name == "nt" and cmd[0] in ("npx", "npm", "node")))
    return res.returncode, (res.stdout or "") + (res.stderr or ""), time.time() - t0


def _git_lines(args: list[str]) -> list[str]:
    rc, out, _ = _run(["git", *args])
    return [ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()] if rc == 0 else []


def changed_files(base: str) -> list[str]:
    """Files changed on this branch against base, plus uncommitted and untracked files."""
    names = set(_git_lines(["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"]))
    names |= set(_git_lines(["diff", "--name-only", "--diff-filter=ACMR", "HEAD"]))
    names |= set(_git_lines(["ls-files", "--others", "--exclude-standard"]))
    return sorted(n for n in names if (ROOT / n).is_file() and not n.startswith("scratch/"))


def mapped_tests(changed: list[str], test_root: Path | None = None) -> list[str]:
    """Test files for changed src modules: tests named test_<stem>*.py, or files that import the module."""
    test_root = test_root or ROOT / "tests"
    modules = [c for c in changed if c.startswith("src/") and c.endswith(".py") and not c.endswith("__init__.py")]
    if not modules:
        return []
    found: set[str] = set()
    tests = [p for p in test_root.rglob("test_*.py") if "__pycache__" not in p.parts]
    for mod in modules:
        stem = Path(mod).stem
        dotted = mod[:-3].replace("/", ".")
        pat = re.compile(rf"(from|import)\s+{re.escape(dotted)}\b")
        for t in tests:
            if t.stem == f"test_{stem}" or t.stem.startswith(f"test_{stem}_"):
                found.add(t.relative_to(ROOT).as_posix())
                continue
            try:
                if pat.search(t.read_text(encoding="utf-8", errors="replace")):
                    found.add(t.relative_to(ROOT).as_posix())
            except OSError:
                pass
    return sorted(found)


def lint_count(tool: str, output: str) -> int:
    if tool == "ruff":
        m = re.search(r"Found (\d+) error", output)
        return int(m.group(1)) if m else 0
    m = re.search(r"\((\d+) errors?,", output)
    return int(m.group(1)) if m else 0


def judge(name: str, rc: int, out: str, lint: str | None) -> tuple[str, str]:
    if rc == 0:
        return "PASS", ""
    if rc == 5 and ("no tests ran" in out or "deselected" in out):
        return "PASS", "no tests selected"
    if lint and lint in KNOWN_LINT:
        card, allowed = KNOWN_LINT[lint]
        n = lint_count(lint, out)
        if 0 < n <= allowed:
            return "KNOWN", f"{n} errors, named in {card} (limit {allowed})"
        if n > allowed:
            return "FAIL", f"{n} errors, more than the {allowed} named in {card}"
    return "FAIL", _tail(out)


SUMMARY_RE = re.compile(r"Tests\s+\d|\d+ (passed|failed)|Found \d+ error|All checks passed|\d+ problems? \(")


def _tail(out: str) -> str:
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return (lines[-1] if lines else "no output")[:160]


def fast_stages(base: str) -> list[tuple[str, list[str] | None, str | None]]:
    changed = changed_files(base)
    py = [c for c in changed if c.endswith(".py")]
    js = [c for c in changed if c.endswith((".js", ".mjs")) and c.startswith(JS_LINT_ROOTS)]
    tests_changed = [c for c in py if c.startswith("tests/") and Path(c).name.startswith("test_")]
    mapped = [t for t in mapped_tests(changed) if t not in tests_changed]
    print(f"[preflight] base {base}: {len(changed)} changed files, {len(tests_changed)} changed tests, {len(mapped)} mapped tests")
    return [
        ("ruff (changed .py)", RUFF + py if py else None, "ruff"),
        ("eslint (changed .js/.mjs)", ["npx", "eslint", *js] if js else None, "eslint"),
        ("pytest guard", PYTEST_PAR + ["-m", "guard", "tests/unit", "tests/integration"], None),
        # slow-marked tests run in the release tier, not here [CARD-560]
        ("pytest changed tests (not slow)", PYTEST_PAR + ["-m", "not slow", *tests_changed] if tests_changed else None, None),
        ("pytest mapped tests (not slow)", PYTEST_PAR + ["-m", "not slow", *mapped] if mapped else None, None),
        ("vitest", ["npx", "vitest", "run"], None),
    ]


def release_stages() -> list[tuple[str, list[str] | None, str | None]]:
    return [
        ("ruff", RUFF + ["."], "ruff"),
        ("eslint", ["npm", "run", "lint:frontend"], "eslint"),
        ("pytest unit + integration (parallel)", PYTEST_PAR + ["-m", "not serial", "tests/unit", "tests/integration"], None),
        ("pytest serial", PYTEST + ["-m", "serial", "tests/unit", "tests/integration"], None),
        ("honesty validate", HONESTY, None),
        ("vitest", ["npx", "vitest", "run"], None),
        ("smoke", ["npx", "playwright", "test", "tests/e2e/smoke.spec.js", "--reporter=line"], None),
    ]


def run_tier(tier: str, stages) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    t_all = time.time()
    for name, cmd, lint in stages:
        if cmd is None:
            rows.append((name, "SKIP", 0.0, "nothing changed for this stage"))
            print(f"[preflight] {name}: SKIP")
            continue
        print(f"[preflight] {name}: {' '.join(cmd[:8])}{' ...' if len(cmd) > 8 else ''}")
        rc, out, secs = _run(cmd)
        log = OUT / (re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + ".log")
        log.write_text(out, encoding="utf-8")
        result, note = judge(name, rc, out, lint)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
        summary = next((ln.strip() for ln in reversed(plain.splitlines()) if SUMMARY_RE.search(ln)), "")
        rows.append((name, result, secs, note or summary[:160]))
        print(f"[preflight] {name}: {result} ({secs:.0f} s) {note}")
    total = time.time() - t_all
    ok = all(r[1] in ("PASS", "KNOWN", "SKIP") for r in rows)
    lines = [f"# Preflight {tier} ({_dt.datetime.now():%Y-%m-%d %H:%M})", "", "| Stage | Result | Seconds | Note |", "|---|---|---:|---|"]
    lines += [f"| {n} | {r} | {s:.0f} | {str(t).replace('|', '/')} |" for n, r, s, t in rows]
    lines += ["", f"Total: {total:.0f} s. Result: {'GREEN' if ok else 'RED'}."]
    (OUT / "last.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--fast", action="store_true")
    g.add_argument("--release", action="store_true")
    p.add_argument("--base", default="qa")
    a = p.parse_args(argv)
    if a.fast:
        return run_tier("fast", fast_stages(a.base))
    return run_tier("release", release_stages())


if __name__ == "__main__":
    sys.exit(main())
