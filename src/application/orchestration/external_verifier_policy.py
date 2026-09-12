"""
Standing external verifier policy [CARD-216 / CARD-220 / CARD-254 / REQ-VERIFY-EXT-* / REQ-VRH-*].

Reflexion/retry only when a named checker returns binary pass/fail
(pytest / schema / health / tool). Missing checker -> honest skip.
Never treat same-model critique as a standing pass
(Shinn Reflexion 2023; Panickssery et al. 2024 same-model judges).

CARD-220 advance rules:
  - verified => advance (verified_advance=True)
  - failed => bounded auto-replan (N=3) then HITL park (never silent advance) [CARD-232]
  - skipped_no_checker never counts as verified advance
  - Execute lane (or checker-bearing phase) does not advance on skip
  - Research/Handoff may continue on honest skip
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from src.domain.orchestration.models import HandoffPacket


class VerifyOutcomeStatus(str, Enum):
    VERIFIED = "verified"
    SKIPPED_NO_CHECKER = "skipped_no_checker"
    FAILED = "failed"


@dataclass(frozen=True)
class VerifyOutcome:
    status: VerifyOutcomeStatus
    verification_passed: bool
    facts: tuple[str, ...] = ()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "verification_passed": self.verification_passed,
            "skipped": self.status == VerifyOutcomeStatus.SKIPPED_NO_CHECKER,
            "facts": list(self.facts),
        }


def resolve_verify_outcome(
    *,
    checker: Optional[str],
    checker_passed: Optional[bool],
    used_same_model_critic: bool = False,
) -> VerifyOutcome:
    """Map checker presence + binary result to standing verify statuses.

    CARD-254 / REQ-VRH-001: LLM self-critique / same-model critic is never standing
    authority - even if a checker name is spoofed alongside the critic flag.
    """
    name = (checker or "").strip()
    # Same-model / LLM self-critique never yields standing verified [REQ-VRH-001].
    if used_same_model_critic:
        return VerifyOutcome(
            status=VerifyOutcomeStatus.SKIPPED_NO_CHECKER,
            verification_passed=False,
            facts=(
                "verify_status: skipped_no_checker "
                "(LLM self-critique / same-model critic is not standing authority)",
            ),
        )
    if not name:
        return VerifyOutcome(
            status=VerifyOutcomeStatus.SKIPPED_NO_CHECKER,
            verification_passed=False,
            facts=("verify_status: skipped_no_checker",),
        )
    if checker_passed is True:
        return VerifyOutcome(
            status=VerifyOutcomeStatus.VERIFIED,
            verification_passed=True,
            facts=(f"verify_status: verified (checker={name})",),
        )
    return VerifyOutcome(
        status=VerifyOutcomeStatus.FAILED,
        verification_passed=False,
        facts=(f"verify_status: failed (checker={name})",),
    )


def phase_lane(phase: Any) -> str:
    """Map phase name to standing catalog lane [CARD-220]."""
    name = (getattr(phase, "name", None) or "").strip().lower()
    for lane in ("research", "handoff", "execute"):
        if name.startswith(lane):
            return lane
    return "generic"


def should_advance_phase(*, status: VerifyOutcomeStatus, phase: Any) -> bool:
    """Standing advance rules [REQ-CATJOB-003]."""
    if status == VerifyOutcomeStatus.VERIFIED:
        return True
    if status == VerifyOutcomeStatus.FAILED:
        return False
    # skipped_no_checker never counts as verified advance.
    lane = phase_lane(phase)
    has_checker = bool((getattr(phase, "verify_checker", None) or "").strip())
    if lane == "execute" or has_checker:
        return False
    # Research / Handoff / generic-without-checker may continue on honest skip.
    return True


def apply_phase_complete_verify_gate(
    orchestrator: Any,
    *,
    phase_id: str,
    output_packet: HandoffPacket,
    checker_passed: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Standing phase-complete gate [REQ-VERIFY-EXT-003 / REQ-CATJOB-003].

    - verified -> complete + advance (verified_advance=True)
    - failed -> park + needs_replan (never silent advance)
    - skipped_no_checker -> complete; advance only when lane allows; never verified_advance
    """
    phase = orchestrator._store.get_phase(phase_id)
    checker = (getattr(phase, "verify_checker", None) or "").strip() or None
    outcome = resolve_verify_outcome(checker=checker, checker_passed=checker_passed)

    merged_facts = list(output_packet.facts or []) + list(outcome.facts)
    packet = HandoffPacket(
        goal=output_packet.goal,
        facts=merged_facts,
        constraints=list(output_packet.constraints or []),
        done_when=output_packet.done_when,
        budget=dict(output_packet.budget or {}),
    )

    base = outcome.as_dict()
    base["verified_advance"] = False
    base["advanced"] = False
    base["needs_replan"] = False
    base["action"] = "none"
    base["lane"] = phase_lane(phase)

    if outcome.status == VerifyOutcomeStatus.FAILED:
        # CARD-232: bounded auto-replan (N=3) then HITL park - never silent advance.
        from src.application.orchestration.bounded_auto_replan import (
            apply_bounded_replan_on_failed,
        )

        replan_out = apply_bounded_replan_on_failed(
            orchestrator,
            phase_id=phase_id,
            fail_facts=list(outcome.facts),
        )
        base.update(replan_out)
        base["status"] = VerifyOutcomeStatus.FAILED.value
        base["verification_passed"] = False
        base["skipped"] = False
        base["advanced"] = False
        base["verified_advance"] = False
        base["lane"] = phase_lane(phase)
        return base

    advance = should_advance_phase(status=outcome.status, phase=phase)
    verified_advance = outcome.status == VerifyOutcomeStatus.VERIFIED and advance

    complete = getattr(orchestrator, "complete_phase", None)
    if not callable(complete):
        raise RuntimeError("orchestrator missing complete_phase")
    try:
        nxt = complete(phase_id, packet, advance=advance)
    except TypeError:
        # Backward-compatible signature without advance kwarg.
        nxt = complete(phase_id, packet) if advance else None
        if not advance:
            # Best-effort: mark done without relying on advance kwarg.
            phase = orchestrator._store.get_phase(phase_id)
            if phase.status.value != "done":
                from src.domain.orchestration.models import PhaseStatus, ReactState

                phase.status = PhaseStatus.DONE
                phase.react_state = ReactState.DONE
                phase.output_packet_json = packet.model_dump_json()
                orchestrator._store.update_phase(phase)
                commit = getattr(orchestrator, "_commit_checkpoint", None)
                if callable(commit):
                    commit(
                        phase,
                        verifier_status=outcome.status.value,
                        hitl_park_state=False,
                    )

    base["advanced"] = bool(advance)
    base["verified_advance"] = bool(verified_advance)
    base["action"] = "advance" if advance else "complete_no_advance"
    base["next_phase_id"] = getattr(nxt, "id", None) if nxt is not None else None
    return base


# --- CARD-254 forced-fail smoke path [REQ-VRH-002] ---------------------------

FORCED_FAIL_CHECKER = "forced_fail"
FORCED_FAIL_FACT = "verify_status: failed (checker=forced_fail)"


def apply_forced_fail_verify_gate(
    orchestrator: Any,
    *,
    phase_id: str,
    reason: str = "forced_fail: binary external smoke",
    output_packet: Optional[HandoffPacket] = None,
) -> Dict[str, Any]:
    """Force binary external FAILED (no LLM) then 232 replan/park [REQ-VRH-002].

    Ensures the phase has a named checker so the standing gate maps to `failed`
    (never skipped_no_checker / never same-model critic). Routes through
    `apply_phase_complete_verify_gate` -> bounded replan cap -> HITL park.
    """
    phase = orchestrator._store.get_phase(phase_id)
    checker = (getattr(phase, "verify_checker", None) or "").strip()
    if not checker:
        phase.verify_checker = FORCED_FAIL_CHECKER
        orchestrator._store.update_phase(phase)
        checker = FORCED_FAIL_CHECKER

    packet = output_packet or HandoffPacket(
        goal=getattr(phase, "success_rule", None) or "forced fail",
        facts=[reason, FORCED_FAIL_FACT],
        constraints=[],
        done_when=getattr(phase, "success_rule", None) or "forced fail",
        budget={},
    )
    # Binary external fail - never LLM self-score.
    out = apply_phase_complete_verify_gate(
        orchestrator,
        phase_id=phase_id,
        output_packet=packet,
        checker_passed=False,
    )
    out["forced_fail"] = True
    out["binary_external"] = True
    out["used_llm_self_critique"] = False
    out["checker"] = checker
    if reason and reason not in (out.get("facts") or []):
        facts = list(out.get("facts") or [])
        facts.insert(0, reason)
        out["facts"] = facts
    return out
