"""Bounded auto-replan on verifier failed [CARD-232 / CARD-254 / REQ-REPLAN-001..005 / REQ-VRH-002].

On failed: reformulate remaining phases against the same success_rule + matched
capability IDs (never silent advance). Cap at MAX_REPLAN_ATTEMPTS=3; after N
fails => HITL park with reason. skipped_no_checker never triggers replan.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from src.domain.orchestration.models import PhaseSpec

logger = logging.getLogger(__name__)

# Locked constant [REQ-REPLAN-002]
MAX_REPLAN_ATTEMPTS = 3


def replan_count_from_checkpoint(checkpoint: Any) -> int:
    """Read durable replan_count from latest checkpoint (0 if missing)."""
    if checkpoint is None:
        return 0
    if isinstance(checkpoint, dict):
        raw = checkpoint.get("replan_count", 0)
    else:
        raw = getattr(checkpoint, "replan_count", 0)
    try:
        return max(0, int(raw or 0))
    except (TypeError, ValueError):
        return 0


def last_fail_reason_from_checkpoint(checkpoint: Any) -> str:
    if checkpoint is None:
        return ""
    if isinstance(checkpoint, dict):
        return str(checkpoint.get("last_fail_reason") or "")
    return str(getattr(checkpoint, "last_fail_reason", "") or "")


def should_auto_replan(replan_count: int) -> bool:
    """True when another auto-replan is allowed (count < N)."""
    return int(replan_count) < MAX_REPLAN_ATTEMPTS


def refuse_infinite_replan(replan_count: int) -> bool:
    """Hard stop: True when further auto-replan would be an infinite loop [REQ-VRH-002]."""
    return int(replan_count) >= MAX_REPLAN_ATTEMPTS



def build_replan_phase_specs(
    *,
    success_rule: str,
    verify_checker: Optional[str] = "pytest",
    agent_id: Optional[str] = None,
) -> List[PhaseSpec]:
    """Reformulate remaining standing phases against the same success_rule."""
    rule = (success_rule or "").strip() or "complete the job success rule"
    checker = (verify_checker or "").strip() or "pytest"
    return [
        PhaseSpec(
            name="Formulate",
            success_rule=f"Reformulate remaining plan for: {rule}",
            assigned_agent_id=agent_id,
            verify_checker=None,
        ),
        PhaseSpec(
            name="Execute",
            success_rule=rule,
            assigned_agent_id=agent_id,
            verify_checker=checker,
        ),
    ]


def _fail_reason_from_facts(facts: Sequence[str] | None) -> str:
    joined = "; ".join(str(f) for f in (facts or []) if f)
    if joined:
        return joined[:500]
    return "verifier failed"


def apply_bounded_replan_on_failed(
    orchestrator: Any,
    *,
    phase_id: str,
    fail_facts: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """
    Standing failed-path [REQ-REPLAN-001..004].

    - replan_count < N => auto-replan remaining phases (same success_rule + matched IDs)
    - replan_count >= N => HITL park with reason (4th fail)
    Never silent advance / never auto-success.
    """
    phase = orchestrator._store.get_phase(phase_id)
    job = orchestrator._store.get_job(phase.job_id)
    prior_cp = orchestrator.get_latest_checkpoint(phase.job_id)
    count = replan_count_from_checkpoint(prior_cp)
    reason = _fail_reason_from_facts(fail_facts)
    matched = list(orchestrator.matched_capability_ids_for_job(phase.job_id) or [])
    success_rule = (
        getattr(job, "success_rule", None)
        or getattr(phase, "success_rule", None)
        or ""
    ).strip()
    checker = (getattr(phase, "verify_checker", None) or "").strip() or "pytest"

    base: Dict[str, Any] = {
        "status": "failed",
        "verification_passed": False,
        "skipped": False,
        "facts": list(fail_facts or []) or [f"verify_status: failed (checker={checker})"],
        "verified_advance": False,
        "advanced": False,
        "needs_replan": False,
        "action": "none",
        "replan_count": count,
        "last_fail_reason": reason,
        "replan_exhausted": False,
        "matched_capability_ids": list(matched),
        "success_rule": success_rule,
    }

    if should_auto_replan(count) and not refuse_infinite_replan(count):
        new_count = count + 1
        specs = build_replan_phase_specs(
            success_rule=success_rule,
            verify_checker=checker,
            agent_id=getattr(job, "agent_id", None),
        )
        updated = orchestrator.replan_job(phase.job_id, specs)
        # Preserve matched IDs; stamp durable replan_count + last fail reason.
        continue_phase = orchestrator._store.get_phase(updated.current_phase_id)
        commit = getattr(orchestrator, "_commit_checkpoint", None)
        if callable(commit):
            commit(
                continue_phase,
                verifier_status="failed",
                hitl_park_state=False,
                matched_capability_ids=matched,
                replan_count=new_count,
                last_fail_reason=reason,
            )
        _emit_journey(
            orchestrator,
            job_id=phase.job_id,
            kind="replan",
            payload={
                "replan_count": new_count,
                "max_replan_attempts": MAX_REPLAN_ATTEMPTS,
                "last_fail_reason": reason,
                "success_rule": success_rule,
                "matched_capability_ids": list(matched),
                "failed_phase_id": phase_id,
                "continue_phase_id": getattr(continue_phase, "id", None),
            },
        )
        base["action"] = "replan"
        base["needs_replan"] = True
        base["replan_count"] = new_count
        base["last_fail_reason"] = reason
        base["next_phase_id"] = getattr(continue_phase, "id", None)
        logger.info(
            "Auto-replan job=%s count=%s/%s reason=%s",
            phase.job_id,
            new_count,
            MAX_REPLAN_ATTEMPTS,
            reason[:120],
        )
        return base

    # Cap reached: HITL park with reason [REQ-REPLAN-002]
    park = getattr(orchestrator, "park_phase", None)
    if callable(park):
        try:
            park(phase_id, verifier_status="failed")
        except TypeError:
            park(phase_id)
        # Re-stamp checkpoint with exhausted count + last fail reason.
        refreshed = orchestrator._store.get_phase(phase_id)
        commit = getattr(orchestrator, "_commit_checkpoint", None)
        if callable(commit):
            commit(
                refreshed,
                verifier_status="failed",
                hitl_park_state=True,
                matched_capability_ids=matched,
                replan_count=count,
                last_fail_reason=reason,
            )
    else:
        orchestrator.fail_phase(phase_id, reason)

    _emit_journey(
        orchestrator,
        job_id=phase.job_id,
        kind="replan_park",
        payload={
            "replan_count": count,
            "max_replan_attempts": MAX_REPLAN_ATTEMPTS,
            "last_fail_reason": reason,
            "replan_exhausted": True,
            "phase_id": phase_id,
            "success_rule": success_rule,
            "matched_capability_ids": list(matched),
        },
    )
    base["action"] = "park"
    base["needs_replan"] = False
    base["replan_exhausted"] = True
    base["replan_count"] = count
    base["last_fail_reason"] = reason
    logger.warning(
        "Replan exhausted job=%s count=%s park reason=%s",
        phase.job_id,
        count,
        reason[:120],
    )
    return base


def _emit_journey(
    orchestrator: Any,
    *,
    job_id: str,
    kind: str,
    payload: Dict[str, Any],
) -> None:
    save_ev = getattr(getattr(orchestrator, "_store", None), "save_standing_journey_event", None)
    if not callable(save_ev):
        return
    try:
        save_ev(job_id=job_id, kind=kind, payload=payload)
    except Exception as exc:  # noqa: BLE001
        logger.debug("replan journey event soft-fail: %s", exc)
