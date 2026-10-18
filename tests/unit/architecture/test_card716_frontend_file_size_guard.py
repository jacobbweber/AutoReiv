"""CARD-716 guard test: Frontend files under src/web/ stay <= 800 lines, and unused store/window globals are retired."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[3]
WEB_ROOT = REPO_ROOT / "src" / "web"
MAX_LINES = 800


def test_every_frontend_file_under_src_web_is_at_most_800_lines():
    offenders: list[str] = []
    for path in sorted(WEB_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {".js", ".mjs", ".css", ".html"}:
            continue
        line_count = sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
        if line_count > MAX_LINES:
            rel = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel} ({line_count} lines > {MAX_LINES})")
    assert not offenders, "Frontend files exceeding 800 lines:\n  " + "\n  ".join(offenders)


def test_store_js_retires_unused_exports():
    store_js = (WEB_ROOT / "static" / "modules" / "state" / "store.js").read_text(encoding="utf-8")
    for retired in ("function createStore", "function updateState", "function subscribeState"):
        assert retired not in store_js, f"store.js still defines retired export: {retired}"


def test_retired_window_studio_globals_not_assigned():
    static_root = WEB_ROOT / "static"
    for path in sorted(static_root.rglob("*.js")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT).as_posix()
        assert "window.__autoreivSwitchTab" not in text, f"{rel} still uses window.__autoreivSwitchTab"
        assert "window.openSkillStudioForSkill" not in text, f"{rel} still uses window.openSkillStudioForSkill"
        assert "window.openToolsStudio" not in text, f"{rel} still uses window.openToolsStudio"
