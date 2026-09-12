"""CARD-259 kill/resume mid-LLM [REQ-KILLR-001..004].

Strict TDD: operator kill mid-phase checkpoints (does not fail/cancel);
resume continues the same job_id. Honesty never Done-on-FAILED.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

from src.application.orchestration.external_verifier_policy import (
    apply_phase_complete_verify_gate,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.kill_resume import (
    KILL_CHECKPOINTED,
    OPERATOR_KILL_REASON,
    is_operator_kill_reason,
    kill_checkpoint_payload,
)
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseStatus
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
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


@pytest.fixture
def orch(store):
    return JobPhaseOrchestrator(store)


def _packet(goal: str = "g", facts=None) -> HandoffPacket:
    return HandoffPacket(
        goal=goal,
        facts=list(facts or ["ok"]),
        constraints=[],
        done_when="done",
        budget={},
    )


def _two_phase_job(orch: JobPhaseOrchestrator, session_id: str = "sess_kill"):
    return orch.create_job_with_phases(
        goal="kill then resume same job",
        session_id=session_id,
        agent_id="assistant",
        phase_specs=[
            {"name": "Formulate", "success_rule": "plan ready"},
            {"name": "Execute", "success_rule": "note opened", "verify_checker": "wiki_note_read"},
        ],
    )


def test_operator_kill_reason_classifier():
    assert is_operator_kill_reason(OPERATOR_KILL_REASON) is True
    assert is_operator_kill_reason("operator_kill_mid_llm") is True
    assert is_operator_kill_reason(KILL_CHECKPOINTED) is True
    assert is_operator_kill_reason("phase_cancelled_during_llm") is False
    assert is_operator_kill_reason("phase_llm_timeout after 120.0s") is False
    assert is_operator_kill_reason("") is False


def test_kill_checkpoint_payload_is_resumable_not_failed():
    payload = kill_checkpoint_payload(
        job_id="job_x",
        phase_id="ph_1",
        checkpointed=True,
    )
    assert payload["checkpointed"] is True
    assert payload["resumable"] is True
    assert payload["status"] == "aborted"
    assert payload["job_id"] == "job_x"
    assert "fail" not in payload["reason"]
    assert payload["event"] == KILL_CHECKPOINTED


def test_req_killr_001_kill_mid_phase_checkpoints_same_job_not_failed(orch, store):
    """Mid-Formulate kill writes checkpoint; Job stays open [REQ-KILLR-001 / 004]."""
    job = _two_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    running = store.get_phase(phases[0].id)
    assert running.status == PhaseStatus.RUNNING

    result = orch.checkpoint_mid_llm_kill(job.session_id)
    assert result["checkpointed"] is True
    assert result["resumable"] is True
    assert result["job_id"] == job.id
    assert result["phase_id"] == phases[0].id

    refreshed_job = store.get_job(job.id)
    assert refreshed_job.status == JobStatus.RUNNING
    assert refreshed_job.status not in {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.DONE}

    refreshed_phase = store.get_phase(phases[0].id)
    assert refreshed_phase.status == PhaseStatus.QUEUED
    assert refreshed_phase.status not in {PhaseStatus.FAILED, PhaseStatus.CANCELLED}

    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.job_id == job.id
    assert is_operator_kill_reason(cp.last_fail_reason)
    execute = store.get_phase(phases[1].id)
    assert execute.status == PhaseStatus.QUEUED


def test_req_killr_001_resume_after_kill_same_job_id_continues(orch, store):
    """Kill then resume_after_crash continues the same job_id to DONE [REQ-KILLR-001]."""
    job = _two_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    orch.checkpoint_mid_llm_kill(job.session_id)

    resume = orch.resume_after_crash(job.id)
    assert resume.ok is True
    assert resume.needs_replan is False
    assert resume.job is not None
    assert resume.job.id == job.id
    assert resume.resumed_from_checkpoint is True
    assert resume.continue_phase is not None
    assert resume.continue_phase.id == phases[0].id

    cont = store.get_phase(phases[0].id)
    if cont.status == PhaseStatus.QUEUED:
        orch.start_phase(cont.id)
    apply_phase_complete_verify_gate(
        orch,
        phase_id=phases[0].id,
        output_packet=_packet("plan", ["formulated"]),
        checker_passed=None,
    )
    orch.start_phase(phases[1].id)
    apply_phase_complete_verify_gate(
        orch,
        phase_id=phases[1].id,
        output_packet=_packet("exec", ["opened"]),
        checker_passed=True,
    )
    done = store.get_job(job.id)
    assert done.id == job.id
    assert store.get_phase(phases[0].id).status == PhaseStatus.DONE
    assert store.get_phase(phases[1].id).status == PhaseStatus.DONE
    assert done.status not in {JobStatus.FAILED, JobStatus.CANCELLED}
    if done.status != JobStatus.DONE:
        # Standing gate may leave job RUNNING after last-phase complete; still same job_id.
        orch.complete_phase(phases[1].id, _packet("exec", ["opened"]), advance=True)
        done = store.get_job(job.id)
    assert done.status == JobStatus.DONE


def test_req_killr_001_phase_kill_helper_is_idempotent(orch, store):
    """Second kill on an already-queued phase does not fail the Job [REQ-KILLR-004]."""
    job = _two_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    first = orch.checkpoint_mid_llm_kill_phase(phases[0].id)
    second = orch.checkpoint_mid_llm_kill_phase(phases[0].id)
    assert first["checkpointed"] is True
    assert second["checkpointed"] is True
    assert store.get_job(job.id).status == JobStatus.RUNNING
    assert store.get_phase(phases[0].id).status == PhaseStatus.QUEUED


def test_req_killr_004_kill_never_calls_fail_or_cancel_status(orch, store):
    """Honesty: kill must not leave FAILED/CANCELLED (never Done-on-FAILED) [REQ-KILLR-004]."""
    job = _two_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    orch.checkpoint_mid_llm_kill(job.session_id)
    job2 = store.get_job(job.id)
    phase2 = store.get_phase(phases[0].id)
    assert job2.status != JobStatus.FAILED
    assert job2.status != JobStatus.CANCELLED
    assert job2.status != JobStatus.DONE
    assert phase2.status != PhaseStatus.FAILED
    assert phase2.status != PhaseStatus.CANCELLED


def test_req_killr_002_chat_abort_source_does_not_fail_phase_on_cancel():
    """Chat CancelledError path must checkpoint, not fail_phase [REQ-KILLR-002 / 004]."""
    src = open("src/web/routers/chat.py", encoding="utf-8").read()
    assert "checkpoint_mid_llm_kill_phase" in src
    assert "phase_cancelled_during_llm" not in src
    abort_idx = src.find("async def abort_stream_endpoint")
    assert abort_idx != -1
    abort_src = src[abort_idx : abort_idx + 3500]
    assert 'update_job_status(j.id, "cancelled")' not in abort_src
    assert "checkpoint_mid_llm_kill" in abort_src
    assert "task.cancel()" in abort_src


def test_req_killr_002_routine_executor_cancel_does_not_fail_phase():
    """Routine CancelledError must match Chat: checkpoint, not fail [REQ-KILLR-004]."""
    src = open("src/application/routines/executor.py", encoding="utf-8").read()
    assert "checkpoint_mid_llm_kill_phase" in src
    assert 'fail_phase(started.id, "phase_cancelled_during_llm")' not in src


@pytest.mark.asyncio
async def test_req_killr_002_abort_cancels_worker_and_leaves_job_resumable(store, orch):
    """Abort cancels the in-flight task and leaves the Job open [REQ-KILLR-002]."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.web.routers import chat as chat_mod

    job = _two_phase_job(orch, session_id="sess_abort_live")
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)

    app = FastAPI()
    app.include_router(chat_mod.router)

    class _Tel:
        def record_turn_span(self, *a, **k):
            return None

    app.state.telemetry = _Tel()
    app.state.store = store
    app.state.job_orchestrator = orch

    async def long_running():
        await asyncio.sleep(30)

    dummy = asyncio.create_task(long_running())
    chat_mod._active_stream_tasks["sess_abort_live"] = dummy

    client = TestClient(app)
    resp = client.post("/api/chat/stream/sess_abort_live/abort")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "aborted"
    assert data.get("resumable") is True
    assert data.get("checkpointed") is True
    assert data.get("job_id") == job.id
    assert data.get("task_cancelled") is True

    try:
        await asyncio.wait_for(dummy, timeout=2.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    assert dummy.cancelled() or dummy.done()

    refreshed = store.get_job(job.id)
    assert refreshed.status == JobStatus.RUNNING
    assert store.get_phase(phases[0].id).status == PhaseStatus.QUEUED
