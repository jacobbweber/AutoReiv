"""CARD-219 Job/Phase crash-resume checkpoints [REQ-RESUME-001..005].

Strict TDD: kill mid-phase => same job_id advances from durable checkpoint.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.orchestration.external_verifier_policy import (
    apply_phase_complete_verify_gate,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
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


def _three_phase_job(orch: JobPhaseOrchestrator):
    return orch.create_job_with_phases(
        goal="ship with resume",
        session_id="sess_resume",
        agent_id="assistant",
        phase_specs=[
            {"name": "Research", "success_rule": "notes"},
            {"name": "Build", "success_rule": "built"},
            {"name": "Verify", "success_rule": "green", "verify_checker": "pytest"},
        ],
    )


def test_req_resume_001_checkpoint_durable_after_phase_commit(orch, store):
    """After phase commit, checkpoint on disk has job_id, phase index, verifier, HITL [REQ-RESUME-001]."""
    job = _three_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    outcome = apply_phase_complete_verify_gate(
        orch,
        phase_id=phases[0].id,
        output_packet=_packet("ship", ["notes gathered"]),
        checker_passed=None,
    )
    assert outcome["status"] == "skipped_no_checker"

    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.job_id == job.id
    assert cp.phase_index == 0
    assert cp.verifier_status == "skipped_no_checker"
    assert cp.hitl_park_state is False

    # Park second phase -> HITL park state true on checkpoint
    nxt = store.get_job(job.id)
    assert nxt.current_phase_id == phases[1].id
    orch.start_phase(phases[1].id)
    orch.park_phase(phases[1].id)
    cp2 = orch.get_latest_checkpoint(job.id)
    assert cp2 is not None
    assert cp2.job_id == job.id
    assert cp2.phase_index == 1
    assert cp2.hitl_park_state is True


def test_req_resume_001_failed_verifier_checkpoint(orch, store):
    """Failed verifier stamps durable checkpoint; CARD-232 auto-replans (count=1)."""
    job = orch.create_job_with_phases(
        goal="verify fail",
        session_id="sess_vf",
        agent_id="assistant",
        phase_specs=[
            {
                "name": "Check",
                "success_rule": "done when pytest passes",
                "verify_checker": "pytest",
            }
        ],
        success_rule="done when pytest passes",
    )
    phase = store.list_phases_for_job(job.id)[0]
    orch._matched_ids[job.id] = ["tool.health_probe"]
    orch._commit_checkpoint(
        phase,
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=["tool.health_probe"],
    )
    orch.start_phase(phase.id)
    gate = apply_phase_complete_verify_gate(
        orch,
        phase_id=phase.id,
        output_packet=_packet("verify fail"),
        checker_passed=False,
    )
    assert gate["status"] == "failed"
    assert gate.get("action") == "replan"
    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.verifier_status == "failed"
    assert int(cp.replan_count) == 1
    assert cp.hitl_park_state is False
    assert list(cp.matched_capability_ids) == ["tool.health_probe"]


def test_req_resume_002_kill_mid_phase_same_job_id_continues(orch, store, temp_db_path):
    """Simulate process kill mid-phase: new orchestrator loads same job_id and continues [REQ-RESUME-002]."""
    job = _three_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    apply_phase_complete_verify_gate(
        orch,
        phase_id=phases[0].id,
        output_packet=_packet("ship"),
        checker_passed=None,
    )
    # Start phase 1 (Build), then "crash" while RUNNING — no commit for phase 1.
    orch.start_phase(phases[1].id)
    crashed = store.get_phase(phases[1].id)
    assert crashed.status == PhaseStatus.RUNNING
    job_id = job.id

    # New process: new store + orchestrator on same DB file.
    store2 = SQLiteStateStore(db_path=temp_db_path)
    orch2 = JobPhaseOrchestrator(store2)
    resume = orch2.resume_after_crash(job_id)

    assert resume.ok is True
    assert resume.needs_replan is False
    assert resume.job.id == job_id
    assert resume.resumed_from_checkpoint is True
    assert resume.checkpoint is not None
    assert resume.checkpoint.phase_index == 0  # last durable commit was phase 0
    # Interrupted running phase is re-queued / continue target (same phase index 1).
    assert resume.continue_phase is not None
    assert resume.continue_phase.index == 1
    assert resume.continue_phase.id == phases[1].id
    refreshed = store2.get_phase(phases[1].id)
    assert refreshed.status in {PhaseStatus.QUEUED, PhaseStatus.RUNNING}
    # Advance same job_id through remaining phases.
    if refreshed.status == PhaseStatus.QUEUED:
        orch2.start_phase(refreshed.id)
    apply_phase_complete_verify_gate(
        orch2,
        phase_id=phases[1].id,
        output_packet=_packet("ship", ["built"]),
        checker_passed=None,
    )
    orch2.start_phase(phases[2].id)
    apply_phase_complete_verify_gate(
        orch2,
        phase_id=phases[2].id,
        output_packet=_packet("ship", ["green"]),
        checker_passed=True,
    )
    done = store2.get_job(job_id)
    assert done.status == JobStatus.DONE
    assert done.id == job_id


def test_req_resume_002_corrupt_or_missing_checkpoint_requires_replan(orch, store, temp_db_path):
    """Replan-from-zero only when checkpoint corrupt/missing [REQ-RESUME-002]."""
    job = _three_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    # No checkpoint written yet (crash before first commit).
    store2 = SQLiteStateStore(db_path=temp_db_path)
    orch2 = JobPhaseOrchestrator(store2)
    resume = orch2.resume_after_crash(job.id)
    assert resume.ok is False
    assert resume.needs_replan is True
    assert resume.resumed_from_checkpoint is False

    # Commit once, then corrupt checkpoint payload.
    apply_phase_complete_verify_gate(
        orch2,
        phase_id=phases[0].id,
        output_packet=_packet("ship"),
        checker_passed=None,
    )
    store2.mark_checkpoint_corrupt(job.id)
    resume2 = orch2.resume_after_crash(job.id)
    assert resume2.ok is False
    assert resume2.needs_replan is True


def test_req_resume_003_resume_payload_exposes_resumed_from_checkpoint(orch, store):
    """Resume result carries operator-visible resumed_from_checkpoint payload [REQ-RESUME-003]."""
    job = _three_phase_job(orch)
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    apply_phase_complete_verify_gate(
        orch,
        phase_id=phases[0].id,
        output_packet=_packet("ship"),
        checker_passed=None,
    )
    orch.start_phase(phases[1].id)
    resume = orch.resume_after_crash(job.id)
    payload = resume.as_dict()
    assert payload["resumed_from_checkpoint"] is True
    assert payload["job_id"] == job.id
    assert "phase_index" in payload
    assert "verifier_status" in payload
    assert "hitl_park_state" in payload


def test_req_resume_003_chat_strip_helper_surfaces_resume_flag():
    """Chat strip helper formats resumed_from_checkpoint for the operator [REQ-RESUME-003]."""
    from src.application.orchestration.crash_resume import format_resume_strip_label

    label = format_resume_strip_label(
        {
            "resumed_from_checkpoint": True,
            "job_id": "job_abc",
            "phase_index": 1,
            "verifier_status": "skipped_no_checker",
            "hitl_park_state": False,
        }
    )
    assert "resumed_from_checkpoint" in label.lower() or "Resumed" in label
