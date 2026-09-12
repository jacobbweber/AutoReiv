# -*- coding: utf-8 -*-
"""CARD-254 Verifier/replan harden [REQ-VRH-001..005].

Binary external only; forced fail -> replan <=3 -> HITL park; no infinite loop;
handoff != replan; Chat standing fail uses phase-complete gate (not fail_phase).
"""

from __future__ import annotations

import inspect
import os
import tempfile

import pytest

from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.bounded_auto_replan import (
    MAX_REPLAN_ATTEMPTS,
    refuse_infinite_replan,
    replan_count_from_checkpoint,
)
from src.application.orchestration.external_verifier_policy import (
    FORCED_FAIL_CHECKER,
    VerifyOutcomeStatus,
    apply_forced_fail_verify_gate,
    resolve_verify_outcome,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_a2a_handoff import (
    create_standing_child_job,
    handoff_must_not_replan,
)
from src.domain.orchestration.models import JobStatus, PhaseStatus
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


def _job_execute(orch, store, *, session_id: str, matched=None, checker="pytest"):
    job = orch.create_job_with_phases(
        goal="card254 forced fail proof",
        session_id=session_id,
        agent_id="assistant",
        phase_specs=[
            {
                "name": "Execute",
                "success_rule": "done when health returns 200",
                "verify_checker": checker,
            },
            {"name": "After", "success_rule": "should-not-auto-advance"},
        ],
        success_rule="done when health returns 200",
    )
    ids = list(matched or ["tool.health_probe", "agent.assistant"])
    phases = store.list_phases_for_job(job.id)
    orch._matched_ids[job.id] = list(ids)
    orch._commit_checkpoint(
        phases[0],
        verifier_status="none",
        hitl_park_state=False,
        matched_capability_ids=ids,
    )
    refreshed = store.get_job(job.id)
    if not getattr(refreshed, "success_rule", ""):
        refreshed.success_rule = "done when health returns 200"
        store.update_job(refreshed)
    return store.get_job(job.id)


def _start_current_execute(orch, store, job):
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
    return orch.start_phase(current.id)


# --- REQ-VRH-001 -------------------------------------------------------------


def test_req_vrh_001_llm_self_critique_never_standing_verified():
    """Same-model / LLM self-critique never yields standing verified [REQ-VRH-001]."""
    # Critic alone
    out = resolve_verify_outcome(
        checker=None,
        checker_passed=True,
        used_same_model_critic=True,
    )
    assert out.status == VerifyOutcomeStatus.SKIPPED_NO_CHECKER
    assert out.verification_passed is False

    # Spoofed checker name + critic still not verified
    spoof = resolve_verify_outcome(
        checker="pytest",
        checker_passed=True,
        used_same_model_critic=True,
    )
    assert spoof.status == VerifyOutcomeStatus.SKIPPED_NO_CHECKER
    assert spoof.verification_passed is False
    assert any("self-critique" in f.lower() or "same-model" in f.lower() for f in spoof.facts)

    # Real binary external still works without critic flag
    ok = resolve_verify_outcome(checker="pytest", checker_passed=True, used_same_model_critic=False)
    assert ok.status == VerifyOutcomeStatus.VERIFIED
    assert ok.verification_passed is True


# --- REQ-VRH-002 -------------------------------------------------------------


def test_req_vrh_002_forced_fail_replan_cap_then_park(orch, store):
    """Forced fail -> replan <=3 -> HITL park; no infinite loop [REQ-VRH-002]."""
    assert MAX_REPLAN_ATTEMPTS == 3
    assert refuse_infinite_replan(3) is True
    assert refuse_infinite_replan(2) is False

    job = _job_execute(orch, store, session_id="sess_vrh002")
    actions = []
    for i in range(3):
        started = _start_current_execute(orch, store, job)
        gate = apply_forced_fail_verify_gate(orch, phase_id=started.id)
        actions.append(gate.get("action"))
        assert gate.get("forced_fail") is True
        assert gate.get("binary_external") is True
        assert gate.get("used_llm_self_critique") is False
        assert gate["status"] == "failed"
        assert gate.get("advanced") is False
        assert gate.get("verified_advance") is False
        assert gate.get("action") == "replan", f"fail#{i+1} should replan, got {gate}"
        cp = orch.get_latest_checkpoint(job.id)
        assert replan_count_from_checkpoint(cp) == i + 1
        assert store.get_job(job.id).status != JobStatus.DONE

    # 4th forced fail => park (cap), never 5th replan
    started4 = _start_current_execute(orch, store, job)
    gate4 = apply_forced_fail_verify_gate(orch, phase_id=started4.id)
    actions.append(gate4.get("action"))
    assert gate4.get("action") == "park"
    assert gate4.get("replan_exhausted") is True
    assert store.get_job(job.id).status == JobStatus.WAITING_APPROVAL
    assert store.get_job(job.id).status != JobStatus.DONE
    cp = orch.get_latest_checkpoint(job.id)
    assert replan_count_from_checkpoint(cp) == 3
    assert cp.hitl_park_state is True
    assert actions == ["replan", "replan", "replan", "park"]

    # Further forced fail must not invent infinite replans
    # (phase may already be parked; starting another execute-like remaining phase)
    phases = store.list_phases_for_job(job.id)
    runnable = [
        p
        for p in phases
        if p.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}
        and (p.verify_checker or "execute" in (p.name or "").lower())
    ]
    if runnable:
        # If still waiting_approval on parked phase, gate should park again / refuse replan
        target = runnable[0]
        if target.status == PhaseStatus.QUEUED:
            target = orch.start_phase(target.id)
        # When already at cap, action must not be unbounded replan
        if target.status == PhaseStatus.RUNNING:
            g5 = apply_forced_fail_verify_gate(orch, phase_id=target.id)
            assert g5.get("action") in {"park", "replan"}
            if g5.get("action") == "replan":
                # Still bounded: count must not exceed MAX
                assert replan_count_from_checkpoint(orch.get_latest_checkpoint(job.id)) <= MAX_REPLAN_ATTEMPTS


def test_req_vrh_002_forced_fail_sets_named_checker_when_missing(orch, store):
    """Forced fail stamps forced_fail checker when missing so path is binary external."""
    job = orch.create_job_with_phases(
        goal="no checker yet",
        session_id="sess_vrh002b",
        agent_id="assistant",
        phase_specs=[{"name": "Execute", "success_rule": "done when health returns 200", "verify_checker": None}],
        success_rule="done when health returns 200",
    )
    orch._matched_ids[job.id] = ["tool.health_probe", "agent.assistant"]
    phase = store.list_phases_for_job(job.id)[0]
    orch._commit_checkpoint(phase, verifier_status="none", hitl_park_state=False, matched_capability_ids=["tool.health_probe", "agent.assistant"])
    started = orch.start_phase(phase.id)
    assert not (started.verify_checker or "").strip()
    gate = apply_forced_fail_verify_gate(orch, phase_id=started.id)
    assert gate["status"] == "failed"
    assert gate.get("action") == "replan"
    assert gate.get("checker") == FORCED_FAIL_CHECKER
    assert store.get_phase(started.id).verify_checker == FORCED_FAIL_CHECKER or gate.get("forced_fail")


# --- REQ-VRH-003 -------------------------------------------------------------


def test_req_vrh_003_handoff_is_not_replan(orch, store):
    """Standing child handoff must not bump replan_count or emit replan spans [REQ-VRH-003]."""
    job = _job_execute(orch, store, session_id="sess_vrh003")
    cp0 = orch.get_latest_checkpoint(job.id)
    before = replan_count_from_checkpoint(cp0)

    # Ensure catalog resolve path exists on orch (create_job_from_catalog_resolve)
    if not hasattr(orch, "create_job_from_catalog_resolve"):
        pytest.skip("orchestrator missing create_job_from_catalog_resolve")

    child = create_standing_child_job(
        orch,
        parent_job_id=job.id,
        intent="delegate health probe specialist",
        session_id="sess_vrh003_child",
        agent_id="assistant",
        role="assistant",
        verify_checker="pytest",
    )
    assert child.id != job.id
    after_cp = orch.get_latest_checkpoint(job.id)
    after = replan_count_from_checkpoint(after_cp)
    journey = build_standing_journey(store, job_id=job.id)
    kinds = [t.get("kind") for t in (journey.get("timeline") or [])]
    # Child create should not add replan kinds on parent
    assert handoff_must_not_replan(
        replan_count_before=before,
        replan_count_after=after,
        journey_kinds=kinds,
    )
    assert before == after == 0
    assert "replan" not in kinds
    assert "replan_park" not in kinds


# --- REQ-VRH-004 -------------------------------------------------------------


def test_req_vrh_004_chat_uses_standing_gate_not_fail_phase():
    """Chat standing named-checker fail uses apply_phase_complete_verify_gate [REQ-VRH-004]."""
    import src.web.routers.chat as chat_mod

    src = inspect.getsource(chat_mod._stream_turn_bound)
    assert "apply_phase_complete_verify_gate" in src
    assert "CARD-254" in src or "REQ-VRH-004" in src
    # Must not dead-end verify fail via fail_phase in the verify-fail branch.
    # Allow fail_phase for timeout/cancel/llm error paths outside verify.
    verify_branch = src
    # The verify-fail segment should return replan/park, not fail_phase(detail)
    assert "return \"replan\"" in verify_branch or "return 'replan'" in verify_branch
    assert "return \"parked\"" in verify_branch or "return 'parked'" in verify_branch
    assert "fail_phase(phase.id, detail)" not in src


# --- REQ-VRH-005 -------------------------------------------------------------


def test_req_vrh_005_no_second_orchestrator_and_forced_fail_export():
    """Extends 216/232 only - forced fail helper lives on standing policy [REQ-VRH-005]."""
    from src.application.orchestration import external_verifier_policy as evp
    from src.application.orchestration import bounded_auto_replan as bar

    assert hasattr(evp, "apply_forced_fail_verify_gate")
    assert not hasattr(evp, "SecondVerifierOrchestrator")
    assert not hasattr(bar, "InfiniteReplanLoop")
    assert refuse_infinite_replan(MAX_REPLAN_ATTEMPTS) is True
