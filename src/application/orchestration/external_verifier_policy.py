"""
Standing external verifier policy [CARD-216 / REQ-VERIFY-EXT-*].

Reflexion/retry only when a named checker returns binary pass/fail
(pytest / schema / health / tool). Missing checker -> honest skip.
Never treat same-model critique as a standing pass
(Shinn Reflexion 2023; Panickssery et al. 2024 same-model judges).
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
    """Map checker presence + binary result to standing verify statuses."""
    name = (checker or "").strip()
    if used_same_model_critic and not name:
        return VerifyOutcome(
            status=VerifyOutcomeStatus.SKIPPED_NO_CHECKER,
            verification_passed=False,
            facts=("verify_status: skipped_no_checker (same-model critic is not standing authority)",),
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


def apply_phase_complete_verify_gate(
    orchestrator: Any,
    *,
    phase_id: str,
    output_packet: HandoffPacket,
    checker_passed: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Standing phase-complete gate [REQ-VERIFY-EXT-003].

    - No verify_checker on phase -> complete with skipped_no_checker facts.
    - Checker present + passed -> complete as verified.
    - Checker present + failed -> fail_phase (do not advance as verified).
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

    if outcome.status == VerifyOutcomeStatus.FAILED:
        orchestrator.fail_phase(phase_id, "; ".join(outcome.facts) or "checker failed")
        return outcome.as_dict()

    orchestrator.complete_phase(phase_id, packet)
    return outcome.as_dict()
