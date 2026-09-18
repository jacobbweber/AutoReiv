"""
Unit tests for Autonomous Telemetry Friction Auditor Routine [CARD-354 / REQ-ROUTINE-010].
"""

import json
from pathlib import Path

import pytest

from src.application.routines.telemetry_friction_auditor import run_telemetry_friction_audit
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.routines.manifests import TELEMETRY_FRICTION_AUDITOR_ROUTINE
from src.domain.routines.models import RoutineStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def user_data_dir(tmp_path: Path):
    data_dir = tmp_path / "user_data"
    data_dir.mkdir()
    wiki_dir = data_dir / "skills" / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "SKILL.md").write_text(
        "---\nname: wiki\ndescription: Wiki SOP\ntools:\n  - wiki_template_create\n  - list_wiki_templates\n---\n# Wiki SOP\n\n## Procedure\nCreate notes.\n",
        encoding="utf-8",
    )
    return data_dir


def _seed_friction_session(store: SQLiteStateStore, session_id: str = "sess_fric_1"):
    sess = store.create_session(agent_id="autoreiv", title="Friction Session")
    # Mutating tool succeeds -> followed immediately by list_wiki_templates
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Create a new template"),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="Creating...",
            tool_calls=[ToolCall(id="tc_1", name="wiki_template_create", arguments={"title": "Test"})],
        ),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.TOOL,
            content=json.dumps({"success": True, "id": "tpl_test"}),
            name="wiki_template_create",
            tool_call_id="tc_1",
        ),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="Checking list...",
            tool_calls=[ToolCall(id="tc_2", name="list_wiki_templates", arguments={})],
        ),
    )
    store.save_message(
        session_id=sess.id,
        agent_id="autoreiv",
        message=ChatMessage(
            role=Role.TOOL,
            content=json.dumps([{"id": "tpl_test"}]),
            name="list_wiki_templates",
            tool_call_id="tc_2",
        ),
    )
    return sess.id


def test_routine_execution_stages_recommendations_without_auto_apply(store, user_data_dir):
    """By default, routine stages recommendations in SQLite without modifying disk SKILL.md."""
    _seed_friction_session(store)
    skill_file = user_data_dir / "skills" / "wiki" / "SKILL.md"
    original_skill_md = skill_file.read_text(encoding="utf-8")

    result = run_telemetry_friction_audit(
        store=store,
        data_dir=user_data_dir,
        routine=TELEMETRY_FRICTION_AUDITOR_ROUTINE,
    )

    assert result["success"] is True
    assert result["incidents_count"] >= 1
    assert result["recommendations_count"] >= 1
    assert result["auto_applied_count"] == 0

    # Verify SKILL.md was NOT modified
    assert skill_file.read_text(encoding="utf-8") == original_skill_md

    # Verify proposal staged in SQLite proposals table
    proposals = store.list_proposals(kind="skill")
    assert len(proposals) >= 1
    assert proposals[0].status == "draft"
    payload = json.loads(proposals[0].payload_json)
    assert payload["skill_id"] == "wiki"
    assert "list_wiki_templates" in payload["proposed_patch"]


def test_routine_execution_with_auto_apply(store, user_data_dir):
    """When auto_apply is explicitly True, routine applies patches to SKILL.md."""
    _seed_friction_session(store)
    skill_file = user_data_dir / "skills" / "wiki" / "SKILL.md"

    custom_routine = TELEMETRY_FRICTION_AUDITOR_ROUTINE.model_copy(deep=True)
    custom_routine.metadata["auto_apply"] = True

    result = run_telemetry_friction_audit(
        store=store,
        data_dir=user_data_dir,
        routine=custom_routine,
    )

    assert result["success"] is True
    assert result["auto_applied_count"] >= 1

    # Verify SKILL.md WAS modified with pitfall bullet
    updated = skill_file.read_text(encoding="utf-8")
    assert "## Common Pitfalls & Forbidden Paths" in updated
    assert "- Do not invoke list_wiki_templates" in updated


async def test_routine_executor_dispatches_auditor(store, user_data_dir):
    """RoutineExecutor intercepts telemetry-friction-auditor and executes audit."""
    _seed_friction_session(store)
    from src.application.routines.executor import RoutineExecutor
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    class FakeKernel:
        def __init__(self, data_dir):
            self.data_dir = str(data_dir)

    telemetry = TelemetryCollector(store=store)
    agent_reg, _ = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        skills_dir=str(user_data_dir / "skills"),
    )


    executor = RoutineExecutor(
        agent_registry=agent_reg,
        kernel=FakeKernel(user_data_dir),
        state_store=store,
        telemetry=telemetry,
    )
    run = await executor.execute_routine(TELEMETRY_FRICTION_AUDITOR_ROUTINE)
    assert run.status == RoutineStatus.SUCCESS
    assert "Audited recent telemetry" in run.output
    assert run.duration_ms >= 0.0





