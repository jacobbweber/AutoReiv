"""Job/Phase crash-resume helpers [CARD-219 / REQ-RESUME-*].

LangGraph-style continue from durable checkpoints — not a second graph engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.domain.orchestration.models import Job, JobPhaseCheckpoint, Phase


@dataclass
class CrashResumeResult:
    """Outcome of resume_after_crash."""

    job: Optional[Job] = None
    checkpoint: Optional[JobPhaseCheckpoint] = None
    continue_phase: Optional[Phase] = None
    ok: bool = False
    needs_replan: bool = False
    resumed_from_checkpoint: bool = False
    reason: str = ""
    matched_capability_ids: list[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        cp = self.checkpoint
        ids = list(self.matched_capability_ids or [])
        if not ids and cp is not None:
            ids = list(getattr(cp, "matched_capability_ids", None) or [])
        return {
            "ok": self.ok,
            "needs_replan": self.needs_replan,
            "resumed_from_checkpoint": self.resumed_from_checkpoint,
            "job_id": self.job.id if self.job else None,
            "phase_index": cp.phase_index if cp else (
                self.continue_phase.index if self.continue_phase else None
            ),
            "phase_id": (
                self.continue_phase.id
                if self.continue_phase
                else (cp.phase_id if cp else None)
            ),
            "verifier_status": cp.verifier_status if cp else None,
            "hitl_park_state": cp.hitl_park_state if cp else False,
            "matched_capability_ids": ids,
            "reason": self.reason,
            **self.extra,
        }


def format_resume_strip_label(payload: Dict[str, Any] | None) -> str:
    """Operator-visible Chat/Observability label for crash-resume [REQ-RESUME-003]."""
    data = payload or {}
    if not data.get("resumed_from_checkpoint"):
        return ""
    phase = data.get("phase_index")
    phase_bit = f" phase {int(phase) + 1}" if phase is not None and phase != "" else ""
    return f"Resumed (resumed_from_checkpoint{phase_bit})"


def verifier_status_from_facts(facts: list[str] | None) -> str:
    joined = " ".join(facts or [])
    if "verify_status: verified" in joined or "verify_status:verified" in joined:
        return "verified"
    if "verify_status: failed" in joined or "verify_status:failed" in joined:
        return "failed"
    if "skipped_no_checker" in joined:
        return "skipped_no_checker"
    return "skipped_no_checker"
