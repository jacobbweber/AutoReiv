"""
Card / spec / steering tools [REQ-SDLC-010..014].
"""

from pathlib import Path

import pytest

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.skills.card_skill import CardSkill
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

CARD_BODY = """# [CARD-100] Demo Card

> **Status**: Discuss
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/demo-card/`
> **Labels**: `type:feature`

---

## 1. Why / Intent
Demo.
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "demo-card").mkdir(parents=True)
    (tmp_path / "AGENTS.md").write_text("# Constitution\n\nSDD and TDD.\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def skill(project: Path) -> CardSkill:
    return CardSkill(default_project_root=str(project))


def test_write_read_list_roundtrip(skill: CardSkill, project: Path):
    written = skill.write_card(content=CARD_BODY, filename="CARD-100-demo-card.md")
    assert written["success"] is True
    assert written["id"] == "CARD-100"
    assert written["status"] == "Discuss"
    listed = skill.list_cards()
    assert any(c["id"] == "CARD-100" for c in listed["cards"])
    read = skill.read_card(card_id="CARD-100")
    assert read["success"] is True
    assert "Demo Card" in read["content"]


def test_ready_requires_spec_then_roundtrip_statuses(skill: CardSkill):
    skill.write_card(content=CARD_BODY, filename="CARD-100-demo-card.md")
    deny = skill.set_card_status(card_id="CARD-100", status="Ready")
    assert deny["success"] is False
    skill.write_spec(slug="demo-card", filename="requirements.md", content="# Requirements\n- REQ-1\n")
    ready = skill.set_card_status(card_id="CARD-100", status="Ready")
    assert ready["success"] is True
    assert ready["status"] == "Ready"
    assert skill.set_card_status(card_id="CARD-100", status="In Progress")["success"] is True
    assert skill.set_card_status(card_id="CARD-100", status="In Review")["success"] is True
    ret = skill.set_card_status(card_id="CARD-100", status="Returned", return_reason="missing REQ-1 test")
    assert ret["success"] is True
    assert ret["status"] == "Returned"
    assert ret["review_rounds"] == 1
    assert "missing REQ-1" in ret["return_reason"]


def test_max_rounds_deny(skill: CardSkill):
    skill.write_card(content=CARD_BODY, filename="CARD-100-demo-card.md")
    skill.write_spec(slug="demo-card", filename="requirements.md", content="# R\n")
    skill.set_card_status(card_id="CARD-100", status="Ready")
    for _ in range(3):
        skill.set_card_status(card_id="CARD-100", status="In Progress")
        skill.set_card_status(card_id="CARD-100", status="In Review")
        skill.set_card_status(card_id="CARD-100", status="Returned", return_reason="gap")
    card = skill.read_card(card_id="CARD-100")
    assert card["review_rounds"] == 3
    denied = skill.set_card_status(card_id="CARD-100", status="In Progress")
    assert denied["success"] is False
    assert "operator" in denied["error"].lower()


def test_spec_read_write_and_steering(skill: CardSkill):
    skill.write_spec(slug="demo-card", filename="design.md", content="# Design\nLoop.\n")
    spec = skill.read_spec(slug="demo-card", filename="design.md")
    assert spec["success"] is True
    assert "Loop" in spec["content"]
    steering = skill.read_steering()
    assert steering["success"] is True
    paths = [f["relative_path"] for f in steering["files"]]
    assert "AGENTS.md" in paths
    assert all(f.get("excerpt") for f in steering["files"])


def test_bootstrap_registers_card_tools_and_hitl():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    from src.application.telemetry.collector import TelemetryCollector

    _, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store))
    for name in (
        "list_cards",
        "read_card",
        "write_card",
        "set_card_status",
        "read_spec",
        "write_spec",
        "read_steering",
    ):
        assert tool_reg.get_tool_definition(name) is not None
    engine = HITLApprovalEngine(store=store)
    assert engine.requires_approval(ToolCall(id="1", name="write_card", arguments={}))
    assert engine.requires_approval(ToolCall(id="2", name="write_spec", arguments={}))
    assert engine.requires_approval(ToolCall(id="3", name="set_card_status", arguments={}))
    assert not engine.requires_approval(ToolCall(id="4", name="list_cards", arguments={}))
