"""CARD-232 Bounded auto-replan on verifier failed [REQ-REPLAN-001..005].

failed -> replan remaining phases against same success_rule + matched IDs (never silent advance).
Cap N=3; 4th fail => HITL park with reason.
skipped_no_checker does NOT replan / never verified advance.
Checkpoint persists replan_count + last fail reason; journey shows replan + park spans.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.bounded_auto_replan import MAX_REPLAN_ATTEMPTS
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


def _job_with_execute(orch, store, *, session_id: str, matched=None):
    """Create a job with Execute (checker=pytest) + seed matched IDs on checkpoint."""
    job = orch.create_job_with_phases(
        goal="bounded replan proof",
        session_id=session_id,
        agent_id="assistant",
        phase_specs=[
            {
                "name": "Execute",
                "success_rule": "done when health returns 200",
                "verify_checker": "pytest",
            },
            {"name": "After", "success_rule": "should-not-auto-advance"},
        ],
        success_rule="done when health returns 200",
    )
    ids = list(matched or ["tool.health_probe", "agent.assistant"])
    # Lock matched IDs on bootstrap checkpoint path.
    phases = store.list_phases_for_job(job.id)
    orch._matched_ids[job.id] = list(ids)
    orch._commit_checkpoint(
        phases[0],
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=ids,
    )
    # Persist success_rule on job if create path did not.
    refreshed = store.get_job(job.id)
    if not getattr(refreshed, "success_rule", ""):
        refreshed.success_rule = "done when health returns 200"
        store.update_job(refreshed)
    return store.get_job(job.id)


def _fail_execute(orch, store, job):
    """Start the current execute-like phase and apply failed verifier gate."""
    phases = store.list_phases_for_job(job.id)
    current = next(
        (
            p
            for p in phases
            if p.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}
            and (p.verify_checker or p.name.lower().startswith("execute"))
        ),
        None,
    )
    if current is None:
        current = next(
            p
            for p in phases
            if p.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}
        )
    started = orch.start_phase(current.id)
    # Ensure checker present so gate maps to failed.
    if not (started.verify_checker or "").strip():
        started.verify_checker = "pytest"
        store.update_phase(started)
        started = store.get_phase(started.id)
    gate = apply_phase_complete_verify_gate(
        orch,
        phase_id=started.id,
        output_packet=_packet(job.goal, ["checker blew up"]),
        checker_passed=False,
    )
    return gate, started


# --- Constant -----------------------------------------------------------------


def test_max_replan_constant_is_three():
    assert MAX_REPLAN_ATTEMPTS == 3


# --- REQ-REPLAN-001 -----------------------------------------------------------


def test_req_replan_001_failed_replans_same_success_rule_and_matched_ids(orch, store):
    """On failed, Job replans remaining phases; same success_rule + matched IDs [REQ-REPLAN-001]."""
    locked = ["tool.health_probe", "agent.assistant"]
    job = _job_with_execute(orch, store, session_id="sess_r001", matched=locked)
    rule_before = store.get_job(job.id).success_rule
    assert rule_before

    gate, failed_phase = _fail_execute(orch, store, job)
    assert gate["status"] == "failed"
    assert gate.get("advanced") is False
    assert gate.get("verified_advance") is False
    assert gate.get("action") == "replan"
    assert gate.get("needs_replan") is True

    # Never silent advance / never DONE on fail.
    assert store.get_job(job.id).status != JobStatus.DONE
    # Failed phase must not remain the advanced winner - cancelled or replaced.
    refreshed_failed = store.get_phase(failed_phase.id)
    assert refreshed_failed.status in {
        PhaseStatus.CANCELLED,
        PhaseStatus.FAILED,
        PhaseStatus.WAITING_APPROVAL,
    }
    # New remaining work exists against same rule.
    phases_after = store.list_phases_for_job(job.id)
    active = [
        p
        for p in phases_after
        if p.status not in {PhaseStatus.DONE, PhaseStatus.CANCELLED, PhaseStatus.FAILED}
    ]
    assert active, "replan must create remaining phases"
    assert any(p.name.lower().startswith("execute") or p.verify_checker for p in active)
    assert store.get_job(job.id).success_rule == rule_before
    assert orch.matched_capability_ids_for_job(job.id) == locked
    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert list(cp.matched_capability_ids) == locked


# --- REQ-REPLAN-002 -----------------------------------------------------------


def test_req_replan_002_cap_n3_fourth_fail_parks_hitl(orch, store):
    """N=3 replans; 4th fail => HITL park with reason (not infinite / not auto-success) [REQ-REPLAN-002]."""
    job = _job_with_execute(orch, store, session_id="sess_r002")
    actions = []
    for i in range(3):
        gate, _ = _fail_execute(orch, store, job)
        actions.append(gate.get("action"))
        assert gate["status"] == "failed"
        assert gate.get("advanced") is False
        assert gate.get("action") == "replan", f"fail#{i+1} should replan, got {gate}"
        cp = orch.get_latest_checkpoint(job.id)
        assert int(getattr(cp, "replan_count", 0) or 0) == i + 1
        assert store.get_job(job.id).status != JobStatus.DONE

    # 4th fail => park
    gate4, parked_phase = _fail_execute(orch, store, job)
    assert gate4["status"] == "failed"
    assert gate4.get("advanced") is False
    assert gate4.get("action") == "park"
    assert gate4.get("replan_exhausted") is True
    assert store.get_phase(parked_phase.id).status == PhaseStatus.WAITING_APPROVAL or any(
        p.status == PhaseStatus.WAITING_APPROVAL for p in store.list_phases_for_job(job.id)
    )
    assert store.get_job(job.id).status == JobStatus.WAITING_APPROVAL
    assert store.get_job(job.id).status != JobStatus.DONE
    cp = orch.get_latest_checkpoint(job.id)
    assert int(getattr(cp, "replan_count", 0) or 0) == 3
    assert getattr(cp, "last_fail_reason", "") or gate4.get("last_fail_reason")
    assert cp.hitl_park_state is True


# --- REQ-REPLAN-003 -----------------------------------------------------------


def test_req_replan_003_skipped_no_checker_does_not_replan(orch, store):
    """skipped_no_checker never triggers replan; still not verified advance [REQ-REPLAN-003]."""
    job = orch.create_job_with_phases(
        goal="skip path",
        session_id="sess_r003",
        agent_id="assistant",
        phase_specs=[
            {"name": "Research", "success_rule": "notes gathered", "verify_checker": None},
            {"name": "Execute", "success_rule": "done when health returns 200", "verify_checker": "pytest"},
        ],
        success_rule="done when health returns 200",
    )
    orch._matched_ids[job.id] = ["tool.wiki_note_search"]
    research = store.list_phases_for_job(job.id)[0]
    orch._commit_checkpoint(
        research,
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=["tool.wiki_note_search"],
    )
    orch.start_phase(research.id)
    gate = apply_phase_complete_verify_gate(
        orch,
        phase_id=research.id,
        output_packet=_packet("skip path", ["gathered"]),
        checker_passed=None,
    )
    assert gate["status"] == "skipped_no_checker"
    assert gate.get("verified_advance") is False
    assert gate.get("action") != "replan"
    assert gate.get("needs_replan") is not True
    cp = orch.get_latest_checkpoint(job.id)
    assert int(getattr(cp, "replan_count", 0) or 0) == 0


def test_req_replan_003_execute_skip_still_not_verified_advance(orch, store):
    """Execute skipped_no_checker still does not verified-advance [REQ-REPLAN-003 / 216]."""
    job = orch.create_job_with_phases(
        goal="exec skip",
        session_id="sess_r003b",
        agent_id="assistant",
        phase_specs=[
            {"name": "Execute", "success_rule": "green", "verify_checker": None},
            {"name": "After", "success_rule": "nope"},
        ],
    )
    ex = store.list_phases_for_job(job.id)[0]
    orch.start_phase(ex.id)
    gate = apply_phase_complete_verify_gate(
        orch,
        phase_id=ex.id,
        output_packet=_packet("exec skip"),
        checker_passed=None,
    )
    assert gate["status"] == "skipped_no_checker"
    assert gate.get("advanced") is False
    assert gate.get("verified_advance") is False
    assert gate.get("action") != "replan"
    assert store.get_job(job.id).status != JobStatus.DONE


# --- REQ-REPLAN-004 -----------------------------------------------------------


def test_req_replan_004_checkpoint_and_journey_spans(orch, store):
    """Checkpoint replan_count + last fail reason; journey replan + park spans [REQ-REPLAN-004]."""
    job = _job_with_execute(orch, store, session_id="sess_r004")

    for _ in range(3):
        gate, _ = _fail_execute(orch, store, job)
        assert gate.get("action") == "replan"
        cp = orch.get_latest_checkpoint(job.id)
        assert int(cp.replan_count) >= 1
        assert isinstance(cp.last_fail_reason, str) and cp.last_fail_reason

    gate4, _ = _fail_execute(orch, store, job)
    assert gate4.get("action") == "park"
    cp = orch.get_latest_checkpoint(job.id)
    assert int(cp.replan_count) == 3
    assert cp.last_fail_reason
    assert cp.hitl_park_state is True

    journey = build_standing_journey(store, job_id=job.id)
    assert journey["ok"] is True
    kinds = [t.get("kind") for t in journey.get("timeline") or []]
    span_names = [s.get("name") for s in journey.get("spans") or []]
    assert "replan" in kinds or any(
        str(n).startswith("standing.replan") for n in span_names
    ), (kinds, span_names)
    assert (
        "replan_park" in kinds
        or "park" in kinds
        or any(
            str(n) in {"standing.replan_park", "standing.park", "standing.hitl_park"}
            for n in span_names
        )
    ), (kinds, span_names)


# --- REQ-REPLAN-005 -----------------------------------------------------------


def test_req_replan_005_no_second_orchestrator():
    """Extends standing path only - no parallel ReplanOrchestrator [REQ-REPLAN-005]."""
    import inspect

    from src.application.orchestration import bounded_auto_replan as bar
    from src.application.orchestration import external_verifier_policy as evp

    assert not hasattr(bar, "ReplanOrchestrator")
    assert not hasattr(bar, "SecondJobGraph")
    src = inspect.getsource(evp.apply_phase_complete_verify_gate)
    assert "bounded" in src.lower() or "replan" in src.lower()
