"""Unit tests for CARD-343: Multi-phase job HITL park status honesty."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.gateway.models import Role
from src.domain.orchestration.models import Job, Phase
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.chat import execute_goal_job_phases


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_run_multi_phase_job_parked_does_not_claim_failed(store, tmp_path):
    session_id = "sess_test_park"
    store.create_session(agent_id="autoreiv", title="Test Park", session_id=session_id)

    job = Job(
        id="job_park_test",
        agent_id="autoreiv",
        goal="Create health note",
        session_id=session_id,
    )
    store.create_job(job)
    phase1 = Phase(
        id="phase_formulate_1",
        job_id=job.id,
        index=0,
        name="Formulate",
        assigned_agent_id="autoreiv",
    )
    store.create_phase(phase1)

    orch = MagicMock()
    orch.get_next_phase.side_effect = [phase1, None]
    orch.start_phase.return_value = phase1

    queue = asyncio.Queue()
    kernel = MagicMock()
    reflexion_engine = MagicMock()
    profile = MagicMock(id="autoreiv")

    with patch("src.web.routers.chat._stream_turn_bound", new_callable=AsyncMock) as mock_stream_turn:
        mock_stream_turn.return_value = "parked"

        await execute_goal_job_phases(
            queue=queue,
            kernel=kernel,
            orch=orch,
            store=store,
            reflexion_engine=reflexion_engine,
            profile=profile,
            job=job,
            session_id=session_id,
            self_verify=False,
            approval_mode="ask",
            data_dir=str(tmp_path / "data"),
        )

    # Collect emitted SSE events
    events = []
    while not queue.empty():
        events.append(await queue.get())

    # Find turn_done event
    turn_done_events = [e for e in events if "turn_done" in e]
    assert len(turn_done_events) >= 1
    turn_done_str = turn_done_events[-1]

    # Verify that turn_done does NOT claim job_failed: true
    assert '"job_failed": true' not in turn_done_str.lower()
    assert '"waiting_approval": true' in turn_done_str.lower()

    # Verify that no token or honesty text falsely claims FAILED
    token_events = [e for e in events if "token" in e]
    for te in token_events:
        assert "FAILED" not in te
        assert "no deliverable claimed" not in te

    # Verify stored assistant messages in parent session
    messages = store.get_messages(session_id)
    assistant_msgs = [m for m in messages if m.role == Role.ASSISTANT]
    for am in assistant_msgs:
        assert "FAILED" not in am.content
        assert "waiting for operator approval" in am.content.lower()
