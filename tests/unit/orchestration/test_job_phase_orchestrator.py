"""
JobPhaseOrchestrator linear next-phase, fail, park, cancel [REQ-ORCH-034].
Does not call the LLM.
"""

import os
import tempfile

import pytest

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.errors import InvalidPhaseTransitionError
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseStatus, ReactState
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def orchestrator(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    return JobPhaseOrchestrator(store)


def _done_packet(goal: str) -> HandoffPacket:
    return HandoffPacket(goal=goal, facts=["ok"], constraints=[], done_when="done")


def test_create_single_phase_job_default_chat_shape(orchestrator):
    job = orchestrator.create_single_phase_job(
        goal="hello",
        session_id="sess_chat",
        agent_id="assistant",
    )
    assert job.status == JobStatus.QUEUED
    assert job.session_id == "sess_chat"
    assert job.agent_id == "assistant"
    assert job.current_phase_id
    phases = orchestrator._store.list_phases_for_job(job.id)
    assert len(phases) == 1
    assert phases[0].index == 0
    assert phases[0].name == "Chat"
    assert phases[0].status == PhaseStatus.QUEUED
    assert phases[0].assigned_agent_id == "assistant"
    packet = HandoffPacket.model_validate_json(phases[0].input_packet_json)
    assert packet.goal == "hello"


def test_linear_next_phase_then_job_done(orchestrator):
    job = orchestrator.create_job_with_phases(
        goal="three steps",
        session_id="sess_lin",
        agent_id="assistant",
        phase_specs=[
            {"name": "Explore", "success_rule": "facts gathered"},
            {"name": "Draft", "success_rule": "draft written", "assigned_agent_id": "coding"},
            {"name": "Verify", "success_rule": "checks pass"},
        ],
    )
    phases = orchestrator._store.list_phases_for_job(job.id)
    assert [p.name for p in phases] == ["Explore", "Draft", "Verify"]
    assert [p.index for p in phases] == [0, 1, 2]
    assert phases[1].assigned_agent_id == "coding"

    first = orchestrator.start_phase(phases[0].id)
    assert first.status == PhaseStatus.RUNNING
    assert first.react_state == ReactState.THINKING
    assert orchestrator._store.get_job(job.id).status == JobStatus.RUNNING

    nxt = orchestrator.complete_phase(first.id, _done_packet("three steps"))
    assert nxt is not None
    assert nxt.name == "Draft"
    assert nxt.status == PhaseStatus.QUEUED
    assert orchestrator._store.get_job(job.id).current_phase_id == nxt.id
    assert orchestrator._store.get_job(job.id).status == JobStatus.RUNNING

    orchestrator.start_phase(nxt.id)
    nxt2 = orchestrator.complete_phase(nxt.id, _done_packet("three steps"))
    assert nxt2 is not None
    assert nxt2.name == "Verify"

    orchestrator.start_phase(nxt2.id)
    assert orchestrator.complete_phase(nxt2.id, _done_packet("three steps")) is None
    done = orchestrator._store.get_job(job.id)
    assert done.status == JobStatus.DONE
    assert all(p.status == PhaseStatus.DONE for p in orchestrator._store.list_phases_for_job(job.id))


def test_fail_phase_does_not_advance(orchestrator):
    job = orchestrator.create_job_with_phases(
        goal="fail mid",
        session_id="sess_fail",
        agent_id="assistant",
        phase_specs=[{"name": "A", "success_rule": "a"}, {"name": "B", "success_rule": "b"}],
    )
    phases = orchestrator._store.list_phases_for_job(job.id)
    orchestrator.start_phase(phases[0].id)
    failed = orchestrator.fail_phase(phases[0].id, "provider timeout")
    assert failed.status == JobStatus.FAILED
    assert failed.current_phase_id == phases[0].id
    reloaded = orchestrator._store.list_phases_for_job(job.id)
    assert reloaded[0].status == PhaseStatus.FAILED
    assert reloaded[0].react_state == ReactState.FAILED
    assert reloaded[1].status == PhaseStatus.QUEUED
    with pytest.raises(InvalidPhaseTransitionError):
        orchestrator.complete_phase(phases[0].id, _done_packet("fail mid"))


def test_park_phase_does_not_advance(orchestrator):
    job = orchestrator.create_job_with_phases(
        goal="hitl",
        session_id="sess_park",
        agent_id="assistant",
        phase_specs=[{"name": "A", "success_rule": "a"}, {"name": "B", "success_rule": "b"}],
    )
    phases = orchestrator._store.list_phases_for_job(job.id)
    orchestrator.start_phase(phases[0].id)
    parked = orchestrator.park_phase(phases[0].id)
    assert parked.status == JobStatus.WAITING_APPROVAL
    reloaded = orchestrator._store.get_phase(phases[0].id)
    assert reloaded.status == PhaseStatus.WAITING_APPROVAL
    assert reloaded.react_state == ReactState.PARKED
    assert orchestrator._store.get_phase(phases[1].id).status == PhaseStatus.QUEUED
    with pytest.raises(InvalidPhaseTransitionError):
        orchestrator.complete_phase(phases[0].id, _done_packet("hitl"))


def test_cancel_job_cancels_incomplete_phases(orchestrator):
    job = orchestrator.create_job_with_phases(
        goal="stop",
        session_id="sess_cancel",
        agent_id="assistant",
        phase_specs=[{"name": "A", "success_rule": "a"}, {"name": "B", "success_rule": "b"}],
    )
    phases = orchestrator._store.list_phases_for_job(job.id)
    orchestrator.start_phase(phases[0].id)
    cancelled = orchestrator.cancel_job(job.id)
    assert cancelled.status == JobStatus.CANCELLED
    reloaded = orchestrator._store.list_phases_for_job(job.id)
    assert all(p.status == PhaseStatus.CANCELLED for p in reloaded)
    with pytest.raises(InvalidPhaseTransitionError):
        orchestrator.start_phase(phases[1].id)
