"""
Integration tests for Visual Goal Mode & Reflexion Streaming [REQ-CHAT-010 - REQ-CHAT-014].
CARD-099: default job+phase, persisted goal phases, verify honest skip [REQ-ORCH-035, REQ-ORCH-039, REQ-ORCH-040, REQ-ORCH-041].
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
        side_effect=AssertionError("goal formulate must not call run_turn")
    )
    app.state.kernel.stream_turn = fake_stream_turn
    return app


@pytest.mark.asyncio
async def test_chat_stream_goal_mode_events(stream_app):
    """Assert that goal_mode=True emits plan_formulated and parks for review [REQ-CHAT-010]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_goal",
                "content": "Scan files and generate report",
                "goal_mode": True,
                "self_verify": False,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: plan_formulated" in body
        assert "event: approval_required" in body
        assert "goal_plan_review" in body
        assert "event: step_start" not in body
        assert "event: turn_done" in body
        assert "event: job_created" in body


@pytest.mark.asyncio
async def test_chat_stream_reflexion_events(stream_app):
    """self_verify without a named checker is an honest skip [REQ-ORCH-041]."""
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
async def test_chat_stream_dual_mode_events(stream_app):
    """goal_mode + self_verify still parks for review; does not execute steps [REQ-CHAT-014]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_goal",
                "content": "Scan files and generate report",
                "goal_mode": True,
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: plan_formulated" in body
        assert "event: approval_required" in body
        assert "event: step_start" not in body
        assert "event: turn_done" in body


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
async def test_default_stream_creates_one_job_one_phase(stream_app):
    """Default chat creates exactly one job and one phase [REQ-ORCH-035]."""
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
        assert "event: job_created" in body
        assert "event: phase_start" in body
        assert "event: phase_complete" in body
        assert "event: turn_done" in body

    jobs = stream_app.state.store.list_jobs_for_session("test_sess_default_job")
    assert len(jobs) == 1
    phases = stream_app.state.store.list_phases_for_job(jobs[0].id)
    assert len(phases) == 1
    assert jobs[0].status.value == "done"
    assert phases[0].status.value == "done"
    stream_app.state.kernel.run_turn.assert_not_called()


@pytest.mark.asyncio
async def test_goal_mode_persists_phases_and_waits_for_approve(stream_app):
    """Goal formulate persists N phases and does not execute until resume after approve [REQ-ORCH-039, REQ-ORCH-040]."""
    stream_app.state.store.create_session(session_id="test_sess_goal_persist", agent_id="assistant", title="Persist")
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_persist",
                "content": "Scan files and generate report",
                "goal_mode": True,
            },
        )
        assert first.status_code == 200
        assert "event: plan_formulated" in first.text
        assert "event: step_start" not in first.text
        jobs = stream_app.state.store.list_jobs_for_session("test_sess_goal_persist")
        assert len(jobs) == 1
        phases = stream_app.state.store.list_phases_for_job(jobs[0].id)
        assert len(phases) == 2
        assert all(p.status.value in {"queued", "waiting_approval"} for p in phases)
        assert jobs[0].status.value == "waiting_approval"

        pending = stream_app.state.store.get_pending_approvals("test_sess_goal_persist")
        assert pending
        assert pending[0]["tool_name"] == "goal_plan_review"
        appr_id = pending[0]["id"]
        decide = await ac.post(
            f"/api/approvals/{appr_id}/decision",
            json={"decision": "APPROVED", "session_id": "test_sess_goal_persist"},
        )
        assert decide.status_code == 200
        second = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_persist",
                "content": "",
                "resume": True,
            },
        )
        assert second.status_code == 200
        assert "event: step_start" in second.text
        assert "event: step_complete" in second.text
        assert "event: turn_done" in second.text
        phases_after = stream_app.state.store.list_phases_for_job(jobs[0].id)
        assert all(p.status.value == "done" for p in phases_after)
        users = [m for m in stream_app.state.store.get_messages("test_sess_goal_persist") if m.role == Role.USER]
        assert len(users) == 1


@pytest.mark.asyncio
async def test_chat_stream_goal_mode_approve_runs_steps(stream_app):
    stream_app.state.store.create_session(session_id="test_sess_goal_gate", agent_id="assistant", title="Gate")
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_gate",
                "content": "Scan files and generate report",
                "goal_mode": True,
            },
        )
        assert first.status_code == 200
        assert "event: plan_formulated" in first.text
        assert "event: step_start" not in first.text
        pending = stream_app.state.store.get_pending_approvals("test_sess_goal_gate")
        assert pending
        assert pending[0]["tool_name"] == "goal_plan_review"
        appr_id = pending[0]["id"]
        decide = await ac.post(
            f"/api/approvals/{appr_id}/decision",
            json={"decision": "APPROVED", "session_id": "test_sess_goal_gate"},
        )
        assert decide.status_code == 200
        second = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_gate",
                "content": "",
                "resume": True,
            },
        )
        assert second.status_code == 200
        assert "event: step_start" in second.text
        assert "event: step_complete" in second.text
        assert "event: turn_done" in second.text
        users = [m for m in stream_app.state.store.get_messages("test_sess_goal_gate") if m.role == Role.USER]
        assert len(users) == 1


@pytest.mark.asyncio
async def test_chat_stream_goal_mode_reject_does_not_run(stream_app):
    stream_app.state.store.create_session(session_id="test_sess_goal_reject", agent_id="assistant", title="Reject")
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_reject",
                "content": "Scan files",
                "goal_mode": True,
            },
        )
        assert first.status_code == 200
        pending = stream_app.state.store.get_pending_approvals("test_sess_goal_reject")
        appr_id = pending[0]["id"]
        await ac.post(
            f"/api/approvals/{appr_id}/decision",
            json={"decision": "REJECTED", "session_id": "test_sess_goal_reject"},
        )
        second = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_goal_reject",
                "content": "",
                "resume": True,
            },
        )
        assert second.status_code == 200
        assert "event: step_start" not in second.text
        assert "Plan rejected" in second.text
        users = [m for m in stream_app.state.store.get_messages("test_sess_goal_reject") if m.role == Role.USER]
        assert len(users) == 1
        jobs = stream_app.state.store.list_jobs_for_session("test_sess_goal_reject")
        assert jobs
        assert jobs[0].status.value == "cancelled"


@pytest.mark.asyncio
async def test_verify_skip_when_no_checker(stream_app):
    """Verify checkbox with no named checker records an honest skip [REQ-ORCH-041]."""
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
        assert "verification_passed" not in body or '"passed": false' in body or '"passed":false' in body
    jobs = stream_app.state.store.list_jobs_for_session("test_sess_verify_skip")
    assert len(jobs) == 1
    phases = stream_app.state.store.list_phases_for_job(jobs[0].id)
    assert len(phases) == 1
    assert phases[0].status.value == "done"
    packet = phases[0].output_packet_json or ""
    assert "skipped" in packet
