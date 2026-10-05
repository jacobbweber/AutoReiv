"""CARD-632: journey report reader tools (read-only, jailed to QA report root)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.journey_qa_tools import JourneyQaTools, default_report_root


def _seed(root: Path, card: str, *, fail: bool = False) -> Path:
    folder = root / card
    folder.mkdir(parents=True)
    runs = [
        {
            "journey": "card-demo",
            "viewport": "desktop",
            "outcome": "fail" if fail else "pass",
            "steps": [
                {
                    "step": "Open app",
                    "status": "pass",
                    "reason": "",
                    "screenshot": str(folder / "ok.png"),
                    "ms": 10,
                },
                {
                    "step": "Click Save",
                    "status": "fail" if fail else "pass",
                    "reason": "Dead button: Save did nothing" if fail else "",
                    "screenshot": str(folder / "fail.png") if fail else str(folder / "ok2.png"),
                    "ms": 20,
                },
            ],
            "notes": [],
            "consoleErrors": ["boom"] if fail else [],
            "failedRequests": [],
        }
    ]
    report = {
        "title": "AutoReiv live QA",
        "startedAt": "Mon Oct 05 2026 12:00:00",
        "base": "http://127.0.0.1:8770",
        "runs": runs,
    }
    path = folder / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    (folder / "summary.md").write_text("# Demo\n\nfail\n" if fail else "# Demo\n\npass\n", encoding="utf-8")
    return path


def test_list_read_summarize_pass_and_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "autoreiv-qa"
    _seed(root, "card-pass", fail=False)
    _seed(root, "card-fail", fail=True)
    monkeypatch.setenv("AUTOREIV_QA_REPORT_DIR", str(root))
    tools = JourneyQaTools()
    assert tools.report_root == root.resolve()

    listed = tools.list_journey_reports(limit=10)
    assert listed["success"] is True
    cards = {r["card"] for r in listed["reports"]}
    assert cards == {"card-pass", "card-fail"}
    fail_row = next(r for r in listed["reports"] if r["card"] == "card-fail")
    assert fail_row["overall"] == "fail" and fail_row["failed_runs"] == 1

    ok = tools.read_journey_report("card-pass")
    assert ok["success"] and ok["runs"][0]["outcome"] == "pass"
    assert "Demo" in ok["summary_md"]

    summ = tools.summarize_journey_failures("card-fail")
    assert summ["success"] and summ["failed"] is True
    assert "Click Save" in summ["summary"]
    assert "Dead button" in summ["summary"]
    assert any(f["step"] == "console error" for f in summ["failures"])

    clean = tools.summarize_journey_failures("card-pass")
    assert clean["success"] and clean["failed"] is False
    assert "All runs passed" in clean["summary"]


def test_jail_refuses_parent_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "autoreiv-qa"
    root.mkdir()
    monkeypatch.setenv("AUTOREIV_QA_REPORT_DIR", str(root))
    tools = JourneyQaTools()
    bad = tools.read_journey_report("../secrets")
    assert bad["success"] is False
    assert "outside" in bad["error"].lower() or "No report" in bad["error"] or "Missing" in bad["error"]


def test_register_tools_marks_read_only():
    reg = ScopedToolRegistry()
    JourneyQaTools(report_root=Path(".")).register_tools(reg)
    for name in ("list_journey_reports", "read_journey_report", "summarize_journey_failures"):
        assert reg.get_tool_risk(name) == "read_only"


def test_default_report_root_uses_temp_when_env_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.delenv("AUTOREIV_QA_REPORT_DIR", raising=False)
    monkeypatch.setattr("src.application.skills.journey_qa_tools.tempfile.gettempdir", lambda: str(tmp_path))
    assert default_report_root() == (tmp_path / "autoreiv-qa").resolve()


def test_developer_ticks_journey_qa_skill():
    text = Path("platform/agents/developer.md").read_text(encoding="utf-8")
    assert "- journey-qa" in text
    skill = Path("platform/skills/journey-qa/SKILL.md").read_text(encoding="utf-8")
    assert "list_journey_reports" in skill
    assert "Does not start a journey run" in skill or "does not start" in skill.lower()
