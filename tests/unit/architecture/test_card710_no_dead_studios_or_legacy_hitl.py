"""CARD-710 guard: retire dead studio mounts in app.js, dead backend no-ops, toolsmith special case in allowed_tools, and duplicate phase session HITL tool rows."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.agent_skills.allowed_tools import domain_line
from src.domain.gateway.models import ChatMessage, Role
from tests.unit.agent_skills.catalog import platform_pack_profile

pytestmark = pytest.mark.guard

ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_app_js_does_not_mount_dead_skill_or_tools_studios():
    """app.js must not import or initialize initSkillStudio / initToolsStudio, and switchTab routes legacy aliases to 'capabilities'."""
    app_js = _read("src/web/static/app.js")
    assert "initSkillStudio" not in app_js
    assert "initToolsStudio" not in app_js
    assert "loadSkillStudio" not in app_js
    assert "loadToolsStudio" not in app_js
    assert "tabName = 'capabilities'" in app_js


def test_dead_backend_no_op_helpers_are_retired():
    """Retired no-op helpers must not remain in user_catalog.py, workshop.py, wiki/store.py, or resolver.py."""
    user_catalog = _read("src/application/skills/user_catalog.py")
    assert "def _mount_skill_tools" not in user_catalog
    assert "def _playbook_tool_handler" not in user_catalog

    workshop = _read("src/application/skills/workshop.py")
    assert "def clear_operator_skill_side_effects" not in workshop

    skills_router = _read("src/web/routers/skills.py")
    assert "clear_operator_skill_side_effects" not in skills_router

    wiki_store = _read("src/domain/wiki/store.py")
    assert "def _seed_starter_notes_if_empty" not in wiki_store

    resolver = _read("src/infrastructure/data/resolver.py")
    assert "def _agent_id_to_snake_case" not in resolver


def test_allowed_tools_domain_line_has_no_toolsmith_id_special_case():
    """allowed_tools.py must not branch on agent_id == 'toolsmith'."""
    allowed_tools_src = _read("src/application/agent_skills/allowed_tools.py")
    assert '"toolsmith"' not in allowed_tools_src
    line = domain_line(platform_pack_profile("autoreiv"))
    assert "No agent covers" in line
    assert "Ask Developer" not in line


def test_hitl_decision_does_not_duplicate_phase_session_tool_row_into_parent_chat(tmp_path: Path):
    """Approving a tool call from a job phase session must save the TOOL row only in the phase session, not duplicate it into the parent chat session [M24 finding]."""
    from fastapi.testclient import TestClient

    from src.application.gateway.gateway_service import MultiProviderGateway
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    store = SQLiteStateStore(db_path=str(tmp_path / "hitl_phase.db"))
    store.initialize_db()
    parent_chat_id = "sess_parent_chat_710"
    phase_session_id = "job_710_phase_0"
    store.create_session(agent_id="autoreiv", title="Parent Chat", session_id=parent_chat_id)
    store.create_session(agent_id="autoreiv", title="Job Phase 0", session_id=phase_session_id)
    store.save_message(
        session_id=phase_session_id,
        agent_id="autoreiv",
        message=ChatMessage(role=Role.USER, content="Execute phase step"),
    )
    appr_id = store.create_approval(
        session_id=phase_session_id,
        agent_id="autoreiv",
        tool_name="cli_exec",
        arguments={"command": "echo ok"},
    )

    app = create_app(
        state_store=store,
        gateway_instance=MultiProviderGateway(default_provider_id="mock"),
        wiki_path=str(tmp_path / "wiki"),
    )
    with TestClient(app) as tc:
        res = tc.post(
            f"/api/approvals/{appr_id}/decision",
            json={"decision": "APPROVED", "session_id": parent_chat_id},
        )
        assert res.status_code == 200

    phase_tools = [m for m in store.get_messages(phase_session_id) if m.role == Role.TOOL]
    parent_tools = [m for m in store.get_messages(parent_chat_id) if m.role == Role.TOOL]
    assert len(phase_tools) == 1
    assert phase_tools[0].name == "cli_exec"
    assert parent_tools == []
