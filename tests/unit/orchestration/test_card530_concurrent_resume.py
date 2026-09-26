"""CARD-530: Approve during a live reply must not leave a phase queued and a job stuck [REQ-530-004/005/008].

Seeded from scratch/c530_race_harness.py, the interleaving seen in job_3bdef1802655 (2026-09-26 ~2:32 PM ET).
"""

from __future__ import annotations

import asyncio

import pytest

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseStatus, ReactState
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store(tmp_path):
    return SQLiteStateStore(db_path=str(tmp_path / "c530.db"))


@pytest.fixture
def orch(store):
    return JobPhaseOrchestrator(store)


def _packet():
    return HandoffPacket(goal="g", facts=["ok"], constraints=[], done_when="d", budget={})


def _job(orch, store, session_id="s530"):
    job = orch.create_job_with_phases(
        goal="build a tool",
        session_id=session_id,
        agent_id="developer",
        phase_specs=[{"name": "Formulate", "success_rule": "plan"}, {"name": "Execute", "success_rule": "done"}],
    )
    phases = store.list_phases_for_job(job.id)
    orch._commit_checkpoint(phases[0], verifier_status="none", hitl_park_state=False)
    return job, phases


# ---------------------------------------------------------------- REQ-530-004 phase ownership

def test_stale_worker_cannot_requeue_a_phase_a_newer_run_started(orch, store):
    job, phases = _job(orch, store)
    p0 = orch.start_phase(phases[0].id)
    old_token = orch.phase_run_token(p0.id)
    assert old_token

    # A second stream resumes before the old worker handles its cancel.
    orch.resume_after_crash(job.id)
    orch.start_phase(p0.id)
    assert orch.phase_run_token(p0.id) != old_token

    # The old worker now checkpoints with its own (stale) token: the phase must stay running.
    result = orch.checkpoint_mid_llm_kill_phase(p0.id, run_token=old_token)
    assert result.get("checkpointed") is False
    assert store.get_phase(p0.id).status == PhaseStatus.RUNNING

    orch.complete_phase(p0.id, _packet())
    assert store.get_phase(p0.id).status == PhaseStatus.DONE
    assert store.get_job(job.id).current_phase_id == phases[1].id


def test_stop_then_resume_still_checkpoints_and_resumes(orch, store):
    """Regression fence (CARD-259): Stop re-queues the running phase and the next send resumes it."""
    job, phases = _job(orch, store, session_id="s530_stop")
    p0 = orch.start_phase(phases[0].id)
    ck = orch.checkpoint_mid_llm_kill("s530_stop")
    assert ck.get("checkpointed") is True
    assert store.get_phase(p0.id).status == PhaseStatus.QUEUED
    resumed = orch.resume_after_crash(job.id)
    assert resumed.resumed_from_checkpoint is True
    orch.start_phase(p0.id)
    orch.complete_phase(p0.id, _packet())
    assert store.get_phase(p0.id).status == PhaseStatus.DONE


def test_the_owning_worker_still_checkpoints_its_own_phase(orch, store):
    job, phases = _job(orch, store, session_id="s530_own")
    p0 = orch.start_phase(phases[0].id)
    token = orch.phase_run_token(p0.id)
    result = orch.checkpoint_mid_llm_kill_phase(p0.id, run_token=token)
    assert result.get("checkpointed") is True
    assert store.get_phase(p0.id).status == PhaseStatus.QUEUED


# ---------------------------------------------------------------- REQ-530-005 no stuck job

def _drain(queue):
    out = []
    while not queue.empty():
        item = queue.get_nowait()
        if item:
            out.append(item)
    return out


def test_refused_complete_fails_phase_and_job_honestly(orch, store):
    from src.web.routers.chat import complete_phase_or_fail

    job, phases = _job(orch, store, session_id="s530_refused")
    p0 = orch.start_phase(phases[0].id)
    orch.checkpoint_mid_llm_kill_phase(p0.id)  # leaves it queued, as the race did
    queue: asyncio.Queue = asyncio.Queue()

    ok = asyncio.run(_run_complete(complete_phase_or_fail, orch, queue, job, store.get_phase(p0.id)))

    assert ok is False
    assert store.get_phase(p0.id).status == PhaseStatus.FAILED
    assert store.get_job(job.id).status == JobStatus.FAILED
    events = "".join(_drain(queue))
    assert "phase_complete" in events and '"status": "failed"' in events
    assert "job_failed" in events
    assert "InvalidPhaseTransitionError" not in events
    assert "Cannot complete phase" not in events


async def _run_complete(fn, orch, queue, job, phase):
    return await fn(orch=orch, queue=queue, job=job, phase=phase, output_packet=_packet())


def test_complete_phase_or_fail_completes_a_running_phase(orch, store):
    from src.web.routers.chat import complete_phase_or_fail

    job, phases = _job(orch, store, session_id="s530_ok")
    p0 = orch.start_phase(phases[0].id)
    queue: asyncio.Queue = asyncio.Queue()
    ok = asyncio.run(_run_complete(complete_phase_or_fail, orch, queue, job, p0))
    assert ok is True
    assert store.get_phase(p0.id).status == PhaseStatus.DONE


# ---------------------------------------------------------------- REQ-530-008 startup repair

def _make_stuck(orch, store, session_id):
    job, phases = _job(orch, store, session_id=session_id)
    p0 = orch.start_phase(phases[0].id)
    orch.checkpoint_mid_llm_kill_phase(p0.id)
    stuck = store.get_phase(p0.id)
    stuck.react_state = ReactState.DONE
    store.update_phase(stuck)
    return job, p0


def test_reconciler_fails_a_job_stuck_the_card_530_way(orch, store):
    from src.application.orchestration.stuck_phase_reconciler import reconcile_stuck_phases

    job, p0 = _make_stuck(orch, store, "s530_stuck")
    fixed = reconcile_stuck_phases(store)

    assert fixed == [job.id]
    phase = store.get_phase(p0.id)
    assert phase.status == PhaseStatus.FAILED
    assert "CARD-530" in (phase.output_packet_json or "")
    assert store.get_job(job.id).status == JobStatus.FAILED
    kinds = [e.get("kind") for e in store.list_standing_journey_events(job.id)]
    assert "reconciled_stuck_phase" in kinds


def test_reconciler_leaves_stop_resumable_jobs_and_is_idempotent(orch, store):
    from src.application.orchestration.stuck_phase_reconciler import reconcile_stuck_phases

    stuck_job, _ = _make_stuck(orch, store, "s530_stuck2")
    ok_job, ok_phases = _job(orch, store, session_id="s530_resumable")
    p0 = orch.start_phase(ok_phases[0].id)
    orch.checkpoint_mid_llm_kill_phase(p0.id)  # queued, react_state empty: resumable after Stop

    assert reconcile_stuck_phases(store) == [stuck_job.id]
    assert reconcile_stuck_phases(store) == []
    assert store.get_phase(p0.id).status == PhaseStatus.QUEUED
    assert store.get_job(ok_job.id).status == JobStatus.RUNNING


def test_store_lists_jobs_by_status(orch, store):
    job, phases = _job(orch, store, session_id="s530_list")
    orch.start_phase(phases[0].id)
    assert job.id in [j.id for j in store.list_jobs_by_status("running")]
    assert job.id not in [j.id for j in store.list_jobs_by_status("done")]
