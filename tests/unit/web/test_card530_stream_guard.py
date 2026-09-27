"""CARD-530: the server refuses a second stream while a turn runs, and draft-proposal decisions write one note
[REQ-530-003, REQ-530-006, REQ-530-008 startup wiring]."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile
from src.web.routers import chat as chat_router

pytestmark = pytest.mark.guard


class _LiveTask:
    def __init__(self):
        self.cancelled = False

    def done(self):
        return False

    def cancel(self):
        self.cancelled = True
        return True


def _stream_app():
    app = FastAPI()
    app.include_router(chat_router.router)
    registry = MagicMock()
    registry.get_profile.return_value = AgentProfile(
        id="developer", name="Developer", description="d", system_prompt="", tools=[], max_turns=5
    )
    app.state.registry = registry
    app.state.kernel = MagicMock()
    app.state.job_orchestrator = MagicMock()
    app.state.reflexion_engine = None
    store = MagicMock()
    store.get_messages.return_value = []
    app.state.store = store
    return app, store


@pytest.mark.parametrize("resume", [True, False])
def test_second_stream_while_a_turn_runs_is_refused_not_killed(resume):
    app, store = _stream_app()
    live = _LiveTask()
    chat_router._active_stream_tasks["sess_530_live"] = live
    try:
        res = TestClient(app).post(
            "/api/chat/stream",
            json={"agent_id": "developer", "session_id": "sess_530_live", "content": "" if resume else "hi", "resume": resume},
        )
        assert res.status_code == 409
        detail = res.json()["detail"]
        assert detail["reason"] == "turn_running"
        assert live.cancelled is False
        assert chat_router._active_stream_tasks["sess_530_live"] is live
        store.save_message.assert_not_called()
    finally:
        chat_router._active_stream_tasks.pop("sess_530_live", None)


def test_a_finished_task_does_not_block_a_new_stream():
    done = MagicMock()
    done.done.return_value = True
    chat_router._active_stream_tasks["sess_530_done"] = done
    try:
        assert chat_router.session_turn_running("sess_530_done") is False
        chat_router._active_stream_tasks["sess_530_done"] = _LiveTask()
        assert chat_router.session_turn_running("sess_530_done") is True
    finally:
        chat_router._active_stream_tasks.pop("sess_530_done", None)


# ---------------------------------------------------------------- REQ-530-006 decision note

@pytest.fixture
def client(tmp_path):
    from src.application.gateway.gateway_service import MultiProviderGateway
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app
    from tests.unit.web.test_hitl_web_api import MockLLM

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    gateway = MultiProviderGateway(default_provider_id="mock")
    gateway.register_provider(MockLLM())
    app = create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))
    with TestClient(app) as tc:
        yield tc, store


def _tool_rows(store, session_id):
    return [m for m in store.get_messages(session_id) if getattr(m, "role", None) == Role.TOOL]


def test_approving_a_draft_proposal_writes_one_note_and_no_tool_rows(client, tmp_path):
    from src.application.orchestration.skill_proposals import propose_tool

    tc, store = client
    parent = "sess_530_parent"
    phase_session = f"{parent}::phase::phase_530"
    store.create_session(agent_id="developer", title="Parent", session_id=parent)
    store.create_session(agent_id="developer", title="Formulate", session_id=phase_session)
    data_dir = tmp_path / "data"
    (data_dir / "skills").mkdir(parents=True)
    created = propose_tool(
        store,
        what="get_weather native tool",
        why="AutoReiv has no weather tool",
        how="native",
        where="skills/weather/SKILL.md",
        data_dir=data_dir,
        session_id=phase_session,
        agent_id="developer",
        pack_id="weather",
        tool_json={"name": "get_weather", "description": "weather", "parameters": {}},
    )
    # The running turn already holds the draft result for this call.
    store.save_message(
        session_id=phase_session,
        agent_id="developer",
        message=ChatMessage(role=Role.TOOL, content='{"status": "draft"}', name="propose_tool", tool_call_id="call_1"),
    )
    before_phase = len(_tool_rows(store, phase_session))

    res = tc.post(f"/api/approvals/{created['approval_id']}/decision", json={"decision": "APPROVED", "session_id": parent})

    assert res.status_code == 200
    body = res.json()
    assert body["resume_chat"] is False
    assert len(_tool_rows(store, phase_session)) == before_phase
    assert _tool_rows(store, parent) == []
    notes = [m for m in store.get_messages(parent) if getattr(m, "name", None) == "hitl_decision"]
    assert len(notes) == 1
    assert "Approved" in notes[0].content and "propose_tool" in notes[0].content


def test_a_parked_tool_approval_still_writes_its_result_and_resumes(client):
    """Regression fence (CARD-470): a real parked tool still gets its TOOL result and a chat resume."""
    tc, store = client
    store.create_session(agent_id="autoreiv", title="Parent", session_id="sess_530_parked")
    appr = store.create_approval(
        session_id="sess_530_parked", agent_id="autoreiv", tool_name="execute_command", arguments={"command": "echo hi"}
    )
    res = tc.post(f"/api/approvals/{appr}/decision", json={"decision": "REJECTED", "session_id": "sess_530_parked"})
    assert res.status_code == 200
    assert res.json().get("resume_chat", True) is True
    assert len(_tool_rows(store, "sess_530_parked")) == 1


# ---------------------------------------------------------------- REQ-530-008 startup wiring

def test_create_app_repairs_a_stuck_job_at_startup(tmp_path):
    from src.application.gateway.gateway_service import MultiProviderGateway
    from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
    from src.domain.orchestration.models import JobStatus, PhaseStatus, ReactState
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app
    from tests.unit.web.test_hitl_web_api import MockLLM

    store = SQLiteStateStore(db_path=str(tmp_path / "startup.db"))
    store.initialize_db()
    orch = JobPhaseOrchestrator(store)
    job = orch.create_job_with_phases(
        goal="g", session_id="s", agent_id="developer",
        phase_specs=[{"name": "Formulate", "success_rule": "plan"}, {"name": "Execute", "success_rule": "done"}],
    )
    p0 = store.list_phases_for_job(job.id)[0]
    orch.start_phase(p0.id)
    orch.checkpoint_mid_llm_kill_phase(p0.id)
    stuck = store.get_phase(p0.id)
    stuck.react_state = ReactState.DONE
    store.update_phase(stuck)

    gateway = MultiProviderGateway(default_provider_id="mock")
    gateway.register_provider(MockLLM())
    create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))

    assert store.get_job(job.id).status == JobStatus.FAILED
    assert store.get_phase(p0.id).status == PhaseStatus.FAILED
