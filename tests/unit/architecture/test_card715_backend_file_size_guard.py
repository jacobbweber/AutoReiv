"""CARD-715: Guard test enforcing the 800-line ceiling across all Python files in src/ and router SQL boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_LINES = 800


def test_all_python_files_in_src_under_800_lines() -> None:
    """Every Python file under src/ must be at or below the 800-line ceiling (.agents/rules/code-quality.md)."""
    src_root = REPO_ROOT / "src"
    over_limit: list[str] = []

    for py_file in sorted(src_root.rglob("*.py")):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_LINES:
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            over_limit.append(f"{rel} ({line_count} lines)")

    assert not over_limit, f"Python files in src/ exceed {MAX_LINES} lines: {over_limit}"


def test_education_routers_contain_no_raw_sql() -> None:
    """Education FastAPI routers must delegate SQL mutations to application/infrastructure repositories."""
    routers_dir = REPO_ROOT / "src" / "web" / "routers"
    for py_file in sorted(routers_dir.glob("education*.py")):
        text = py_file.read_text(encoding="utf-8")
        assert "UPDATE education_mastery" not in text, (
            f"{py_file.name} still executes raw SQL 'UPDATE education_mastery' inside the web router"
        )
        assert "_get_connection()" not in text, (
            f"{py_file.name} still reaches into private repository _get_connection()"
        )
