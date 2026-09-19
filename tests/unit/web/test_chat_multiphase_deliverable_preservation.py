"""Unit tests for CARD-378: Multi-phase job deliverable preservation and option park gating [REQ-CHAT-016, REQ-ORCH-045]."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.domain.gateway.models import ChatMessage, Role
from src.domain.orchestration.models import Job, Phase, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.chat import execute_goal_job_phases


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_formulate_deliverable_preserved_when_execute_fails(store, tmp_path):
    """[REQ-CHAT-016]: Phase 0 deliverable is preserved in saved chat message when Phase 1 fails."""
    session_id = "sess_preservation_test"
    store.create_session(agent_id="autoreiv", title="Preservation Test", session_id=session_id)

    job = Job(
        id="job_deliv_test",
        agent_id="autoreiv",
        goal="Build scaled floorplan",
        session_id=session_id,
    )
    store.create_job(job)

    phase0 = Phase(
        id="phase_formulate_0",
        job_id=job.id,
        index=0,
        name="Formulate",
        assigned_agent_id="autoreiv",
        status=PhaseStatus.QUEUED,
    )
    phase1 = Phase(
        id="phase_execute_1",
        job_id=job.id,
        index=1,
        name="Execute",
        assigned_agent_id="autoreiv",
        status=PhaseStatus.QUEUED,
    )
    store.create_phase(phase0)
    store.create_phase(phase1)

    orch = MagicMock()
    orch.start_phase.side_effect = lambda pid: phase0 if pid == phase0.id else phase1

    queue = asyncio.Queue()
    kernel = MagicMock()
    reflexion_engine = MagicMock()
    profile = MagicMock(id="autoreiv")

    formulate_text = "## Formulate — Floor plan model: 1. Units = inches, 2. Build perimeter walls"

    async def mock_stream_bound_turn(*args, **kwargs):
        phase = kwargs.get("phase")
        phase_sess = kwargs.get("session_id")
        if phase and phase.id == phase0.id:
            # Save the formulate output into the phase session
            store.save_message(
                session_id=phase_sess,
                agent_id="autoreiv",
                message=ChatMessage(role=Role.ASSISTANT, content=formulate_text),
            )
            return "done"
        return "failed"

    with patch("src.web.routers.chat._stream_turn_bound", side_effect=mock_stream_bound_turn):
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

    # Verify what was saved in store for the origin session
    msgs = store.get_messages(session_id)
    assistant_msgs = [m for m in msgs if getattr(m, "role", None) == Role.ASSISTANT]
    assert len(assistant_msgs) >= 1, "Must have saved assistant message"

    last_saved = assistant_msgs[-1].content
    # MUST contain Formulate deliverable
    assert "## Formulate — Floor plan model" in last_saved
    # MUST contain honest failure notice for Phase 1
    assert "FAILED during Execute" in last_saved


@pytest.mark.asyncio
async def test_formulate_with_options_parks_for_operator_choice(store, tmp_path):
    """[REQ-ORCH-045]: Formulate presenting branching options parks for operator decision before Phase 1."""
    session_id = "sess_options_park_test"
    store.create_session(agent_id="autoreiv", title="Options Park Test", session_id=session_id)

    job = Job(
        id="job_options_test",
        agent_id="autoreiv",
        goal="Build scaled floorplan with options",
        session_id=session_id,
    )
    store.create_job(job)

    phase0 = Phase(
        id="phase_opt_0",
        job_id=job.id,
        index=0,
        name="Formulate",
        assigned_agent_id="autoreiv",
        status=PhaseStatus.QUEUED,
    )
    phase1 = Phase(
        id="phase_opt_1",
        job_id=job.id,
        index=1,
        name="Execute",
        assigned_agent_id="autoreiv",
        status=PhaseStatus.QUEUED,
    )
    store.create_phase(phase0)
    store.create_phase(phase1)

    orch = MagicMock()
    orch.start_phase.side_effect = lambda pid: phase0 if pid == phase0.id else phase1

    queue = asyncio.Queue()
    kernel = MagicMock()
    reflexion_engine = MagicMock()
    profile = MagicMock(id="autoreiv")

    options_text = (
        "## Formulate Plan\n\n"
        "Execution path + approval gates:\n"
        "- **Option A. Live build** — drive Blender instance\n"
        "- **Option B. Script handoff** — author python script\n"
        "Suggested next beat: pick a route (A or B) to continue."
    )

    async def mock_stream_bound_turn(*args, **kwargs):
        phase = kwargs.get("phase")
        phase_sess = kwargs.get("session_id")
        if phase and phase.id == phase0.id:
            store.save_message(
                session_id=phase_sess,
                agent_id="autoreiv",
                message=ChatMessage(role=Role.ASSISTANT, content=options_text),
            )
            return "done"
        return "done"

    with patch("src.web.routers.chat._stream_turn_bound", side_effect=mock_stream_bound_turn):
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

    # Assert that orch.park_phase was called or turn ended with waiting_approval
    events = []
    while not queue.empty():
        events.append(await queue.get())

    turn_done_events = [e for e in events if "turn_done" in e]
    assert len(turn_done_events) >= 1
    # Turn done event should indicate waiting for approval / choice
    assert "waiting_approval" in turn_done_events[0]
    # Phase 1 should NOT have been executed
    msgs = store.get_messages(session_id)
    assistant_msgs = [m for m in msgs if getattr(m, "role", None) == Role.ASSISTANT]
    assert len(assistant_msgs) >= 1
    # Assistant message contains the options text
    assert "Option A. Live build" in assistant_msgs[-1].content
    assert "waiting for operator approval" in assistant_msgs[-1].content.lower() or "pick a route" in assistant_msgs[-1].content.lower()

