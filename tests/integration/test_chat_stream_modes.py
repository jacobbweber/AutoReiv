"""
Integration tests for Standing Job-Graph Runtime & Reflexion Streaming.
CARD-215 retires per-prompt goal_mode authority [REQ-JOBGRAPH-001..003].
Legacy CARD-099 verify honest-skip coverage retained.
"""

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
def stream_app():
    store = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=store)
    app.state.store.create_session(session_id="test_sess_stream_goal", agent_id="assistant", title="Goal Test")
    app.state.store.create_session(session_id="test_sess_stream_verify", agent_id="assistant", title="Verify Test")
    app.state.kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(message=ChatMessage(role=Role.ASSISTANT, content=PLAN_JSON))
    )
    app.state.kernel.run_turn = AsyncMock(
        side_effect=AssertionError("standing formulate must not call run_turn")
    )
    app.state.kernel.stream_turn = fake_stream_turn
    return app


@pytest.mark.asyncio
async def test_chat_stream_standing_multi_step_events(stream_app):
    """Standing multi-step formulates+executes without goal_mode or plan-review [REQ-JOBGRAPH-001]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_goal",
                "content": MULTI_STEP,
                "goal_mode": False,
                "self_verify": False,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: plan_formulated" in body
        assert "event: job_created" in body
        assert "event: step_start" in body
        assert "event: step_complete" in body
        assert "event: turn_done" in body
        assert "goal_plan_review" not in body


@pytest.mark.asyncio
async def test_chat_stream_reflexion_events(stream_app):
    """self_verify without a named checker is an honest skip [REQ-ORCH-041, REQ-JOBGRAPH-003]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_verify",
                "content": "Scan files and generate report",
                "goal_mode": False,
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: turn_done" in body
        assert "event: reflexion_verified" in body
        assert '"status": "skipped"' in body or '"status":"skipped"' in body
        assert '"passed": false' in body or '"passed":false' in body


@pytest.mark.asyncio
async def test_chat_stream_goal_mode_flag_ignored_for_short(stream_app):
    """goal_mode is not authority; short prompts stay plain ReAct [REQ-JOBGRAPH-001a, 002]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_goal",
                "content": "What time is it",
                "goal_mode": True,
                "self_verify": False,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: turn_done" in body
        assert "event: plan_formulated" not in body
        assert "goal_plan_review" not in body


@pytest.mark.asyncio
async def test_chat_stream_self_verify_keeps_critiques_off_transcript(stream_app):
    """No named checker: skip, do not invent CRITIQUE user messages [REQ-VERIFY-014, REQ-ORCH-041]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_verify",
                "content": "What time is it",
                "goal_mode": False,
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: reflexion_verified" in body
        assert "skipped" in body
        assert '"passed": true' not in body and '"passed":true' not in body

    messages = stream_app.state.store.get_messages("test_sess_stream_verify")
    assert all("CRITIQUE ON PREVIOUS OUTPUT" not in (m.content or "") for m in messages)


@pytest.mark.asyncio
async def test_chat_stream_reflexion_named_checker_events(stream_app):
    """When a named checker runs, streams attempt, critique (on discrepancy), and verified [CARD-179]."""
    stream_app.state.store.create_session(
        session_id="test_sess_stream_checker", agent_id="assistant", title="Checker Test"
    )
    stream_app.state.reflexion_engine.run_named_checker = AsyncMock(
        return_value={
            "status": "failed",
            "verification_passed": False,
            "discrepancies": ["output lacks required summary"],
            "output": "phase output",
        }
    )
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_checker",
                "content": "Verify system audit",
                "goal_mode": False,
                "self_verify": True,
                "verify_checker": "assert_system_audit",
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: reflexion_attempt" in body
        assert '"attempt": 1' in body or '"attempt":1' in body
        assert "assert_system_audit" in body
        assert "event: reflexion_critique" in body
        assert "output lacks required summary" in body
        assert "event: reflexion_verified" in body
        assert '"passed": false' in body or '"passed":false' in body


@pytest.mark.asyncio
async def test_default_stream_short_turn_no_job(stream_app):
    """Short Chat stays plain ReAct — no Job/Phase rows [REQ-JOBGRAPH-001a]."""
    stream_app.state.store.create_session(session_id="test_sess_default_job", agent_id="assistant", title="Default")
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_default_job",
                "content": "What time is it",
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: turn_done" in body
        assert "event: plan_formulated" not in body

    jobs = stream_app.state.store.list_jobs_for_session("test_sess_default_job")
    assert jobs == []
    stream_app.state.kernel.run_turn.assert_not_called()


@pytest.mark.asyncio
async def test_standing_multi_step_persists_and_executes_phases(stream_app):
    """Standing multi-step persists N phases and executes without approve theatre [REQ-JOBGRAPH-001]."""
    stream_app.state.store.create_session(session_id="test_sess_goal_persist", agent_id="assistant", title="Persist")
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_persist",
                "content": MULTI_STEP,
            },
        )
        assert first.status_code == 200
        assert "event: plan_formulated" in first.text
        assert "event: step_start" in first.text
        assert "goal_plan_review" not in first.text
        jobs = stream_app.state.store.list_jobs_for_session("test_sess_goal_persist")
        assert len(jobs) == 1
        phases = stream_app.state.store.list_phases_for_job(jobs[0].id)
        assert len(phases) == 2
        assert all(p.status.value == "done" for p in phases)
        assert jobs[0].status.value == "done"


@pytest.mark.asyncio
async def test_verify_skip_when_no_checker(stream_app):
    """Verify checkbox with no named checker records an honest skip [REQ-ORCH-041, REQ-JOBGRAPH-003]."""
    stream_app.state.store.create_session(session_id="test_sess_verify_skip", agent_id="assistant", title="Skip")
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_verify_skip",
                "content": "What time is it",
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "skipped" in body
        assert '"passed": true' not in body and '"passed":true' not in body
    jobs = stream_app.state.store.list_jobs_for_session("test_sess_verify_skip")
    assert jobs == []
