"""CARD-633: run_journey is throwaway-only, HITL high-risk, refuses live :8000."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.application.kernel.hitl_engine import DEFAULT_HIGH_RISK_TOOLS, HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety.tool_policy_gate import RISKS_NEEDING_CONFIRM
from src.application.skills.journey_qa_tools import (
    DEFAULT_QA_PORT,
    FORBIDDEN_QA_PORTS,
    JourneyQaTools,
)
from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_run_journey_refuses_live_port_8000():
    tools = JourneyQaTools(report_root=Path("."))
    out = tools.run_journey("card-623-compact-honest", port=8000)
    assert out["success"] is False
    assert "8000" in out["error"]


def test_run_journey_refuses_empty_and_path_escape():
    tools = JourneyQaTools(report_root=Path("."))
    assert tools.run_journey("")["success"] is False
    assert tools.run_journey("../evil")["success"] is False
    assert tools.run_journey(r"C:\Windows\system32")["success"] is False


def test_run_journey_hard_codes_throwaway_via_executor(tmp_path: Path):
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return {"success": True, "data": kwargs["data"], "overall": "pass"}

    tools = JourneyQaTools(report_root=tmp_path, run_executor=fake)
    out = tools.run_journey("card-623-compact-honest", viewports="phone", card="card-623")
    assert out["success"] is True
    assert seen["data"] == "throwaway"
    assert seen["journey_id"] == "card-623-compact-honest"
    assert seen["viewports"] == "phone"
    assert seen["port"] == DEFAULT_QA_PORT
    assert seen["port"] not in FORBIDDEN_QA_PORTS


def test_run_journey_registered_network_and_hitl():
    reg = ScopedToolRegistry()
    JourneyQaTools(report_root=Path(".")).register_tools(reg)
    assert reg.get_tool_risk("run_journey") == "network"
    assert "run_journey" in DEFAULT_HIGH_RISK_TOOLS
    assert "network" in RISKS_NEEDING_CONFIRM

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    hitl = HITLApprovalEngine(store)
    assert hitl.requires_approval(ToolCall(id="1", name="run_journey", arguments={"journey_id": "x"}))


def test_run_journey_timeout_kills_subprocess(tmp_path: Path):
    import subprocess

    tools = JourneyQaTools(
        report_root=tmp_path / "reports",
        checkout=tmp_path,
        live_qa_script=tmp_path / "live_qa.py",
    )
    (tmp_path / "live_qa.py").write_text("# stub\n", encoding="utf-8")

    proc = MagicMock()
    proc.pid = 4242
    proc.poll.return_value = None
    proc.communicate.side_effect = subprocess.TimeoutExpired(cmd="x", timeout=3)

    with patch("src.application.skills.journey_qa_tools.subprocess.Popen", return_value=proc):
        with patch("src.application.skills.journey_qa_tools._kill_process_tree") as kill:
            with patch("src.application.skills.journey_qa_tools.subprocess.run"):
                out = tools.run_journey("card-demo", timeout_seconds=3, port=8770)
    assert out["success"] is False
    assert "timed out" in out["error"].lower()
    kill.assert_called()
    assert JourneyQaTools._active_proc is None


def test_skill_and_developer_include_run_journey():
    skill = Path("platform/skills/journey-qa/SKILL.md").read_text(encoding="utf-8")
    assert "run_journey" in skill
    assert "throwaway" in skill.lower()
    text = Path("platform/agents/developer.md").read_text(encoding="utf-8")
    assert "- journey-qa" in text
