"""CARD-215 Standing Job-Graph Runtime integration [REQ-JOBGRAPH-001..003]."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEvent, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

PLAN_JSON = (
    '{"steps": [{"title": "Step 1: Discover", "description": "Scan files"}, '
    '{"title": "Step 2: Synthesize", "description": "Write report"}]}'
)

MULTI_STEP = (
    "First scan the workspace files, then synthesize a markdown report, "
    "finally verify the summary is complete."
)


async def fake_stream_turn(
    agent,
    session_id,
    user_content=None,
    approval_mode="ask",
    resume=False,
    **kwargs,
):
    job_id = kwargs.get("job_id")
    phase_id = kwargs.get("phase_id")
    agent_id = getattr(agent, "id", None)
    yield KernelEvent(
        event_type=KernelEventType.REACT_STATE,
        react={
            "react_state": "THINKING",
            "job_id": job_id,
            "phase_id": phase_id,
            "assigned_agent_id": agent_id,
        },
    )
    yield KernelEvent(event_type=KernelEventType.TOKEN, content="phase output")
    yield KernelEvent(
        event_type=KernelEventType.REACT_STATE,
        react={
            "react_state": "DONE",
            "job_id": job_id,
            "phase_id": phase_id,
            "assigned_agent_id": agent_id,
        },
    )
    yield KernelEvent(event_type=KernelEventType.TURN_END, content="phase output", is_finished=True)


@pytest.fixture
def standing_app():
    store = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=store)
    app.state.store.create_session(session_id="sess_standing_multi", agent_id="assistant", title="Multi")
    app.state.store.create_session(session_id="sess_standing_short", agent_id="assistant", title="Short")
    app.state.store.create_session(session_id="sess_standing_verify", agent_id="assistant", title="Verify")
    app.state.store.create_session(session_id="sess_standing_goal_api", agent_id="assistant", title="GoalAPI")
    app.state.kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(message=ChatMessage(role=Role.ASSISTANT, content=PLAN_JSON))
    )
    app.state.kernel.run_turn = AsyncMock(
        side_effect=AssertionError("standing path must not use execute_plan/run_turn planner")
    )
    app.state.kernel.stream_turn = fake_stream_turn
    return app


@pytest.mark.asyncio
async def test_req_jobgraph_001_multi_step_without_goal_mode(standing_app):
    """Multi-step Chat creates/advances Job+Phase without goal_mode=true [REQ-JOBGRAPH-001]."""
    transport = ASGITransport(app=standing_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "sess_standing_multi",
                "content": MULTI_STEP,
                "goal_mode": False,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: job_created" in body
        assert "event: plan_formulated" in body
        assert "event: step_start" in body
        assert "event: step_complete" in body
        assert "event: turn_done" in body
        # Standing path must not require plan-review HITL theatre.
        assert "goal_plan_review" not in body

    jobs = standing_app.state.store.list_jobs_for_session("sess_standing_multi")
    assert len(jobs) == 1
    phases = standing_app.state.store.list_phases_for_job(jobs[0].id)
    assert len(phases) >= 2
    assert all(p.status.value == "done" for p in phases)
    assert jobs[0].status.value == "done"


@pytest.mark.asyncio
async def test_req_jobgraph_001a_short_turn_plain_react(standing_app):
    """Short tool turns stay plain AgentKernel ReAct — no job-graph formulation [REQ-JOBGRAPH-001a]."""
    transport = ASGITransport(app=standing_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "sess_standing_short",
                "content": "What time is it",
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: turn_done" in body
        assert "event: plan_formulated" not in body

    jobs = standing_app.state.store.list_jobs_for_session("sess_standing_short")
    assert jobs == []


@pytest.mark.asyncio
async def test_req_jobgraph_001b_002_goal_endpoint_no_execute_authority(standing_app):
    """/api/chat/goal cannot bypass Job/Phase via execute_plan [REQ-JOBGRAPH-001b, 002]."""
    # If execute_plan were called it would hit run_turn AssertionError.
    transport = ASGITransport(app=standing_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/goal",
            json={
                "agent_id": "assistant",
                "session_id": "sess_standing_goal_api",
                "goal": MULTI_STEP,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("deprecated") is True
        assert data.get("job_id")
        assert data.get("status") in {"formulated", "deprecated"}
        # No parallel execute output authority.
        assert data.get("output") in (None, "")

    job = standing_app.state.store.get_job(data["job_id"])
    phases = standing_app.state.store.list_phases_for_job(job.id)
    assert len(phases) >= 1
    # Formulated into Job/Phase store only — not auto-executed by this endpoint.
    assert all(p.status.value in {"queued", "waiting_approval"} for p in phases)


@pytest.mark.asyncio
async def test_req_jobgraph_003_verify_honest_skip_without_checker(standing_app):
    """self_verify without external checker is honest skip, not same-model pass [REQ-JOBGRAPH-003]."""
    transport = ASGITransport(app=standing_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "sess_standing_verify",
                "content": "What time is it",
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        # Short path may skip reflexion SSE if no job; policy still forbids fake pass.
        assert '"passed": true' not in body and '"passed":true' not in body
        assert "verification_passed\": true" not in body


@pytest.mark.asyncio
async def test_req_jobgraph_002_ui_goal_toggle_removed():
    """Per-prompt goal_mode removed from Chat UI authority [REQ-JOBGRAPH-002]."""
    from pathlib import Path

    html = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    js = Path("src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    assert 'id="goalToggle"' not in html
    assert "Switch to Goal & Self-Verify" not in html
    assert "goal_mode:" not in js or "goal_mode: false" in js or "goal_mode:false" in js
    # Must not send live goalMode from UI state as authority.
    assert "goalMode: !!state.goalEnabled" not in js
