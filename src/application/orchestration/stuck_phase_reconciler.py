"""Startup repair for jobs stuck by a concurrent resume [CARD-530 REQ-530-008, D6].

Signature: job ``running``, its current phase ``queued`` with react_state DONE. A turn finished, but a second
run had re-queued the phase, so ``complete_phase`` refused it and nothing ended the job. A phase queued after
Stop has an empty react_state and stays resumable (CARD-259); it is never touched. Idempotent.
"""

from __future__ import annotations

import logging
from typing import Any, List

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.models import PhaseStatus

logger = logging.getLogger(__name__)

STUCK_PHASE_REASON = (
    "Interrupted by a second run while approving (CARD-530): this step finished but could not be recorded. "
    "Send the request again to re-run it."
)


def _react_value(phase: Any) -> str:
    react = getattr(phase, "react_state", None)
    return str(getattr(react, "value", react) or "")


def reconcile_stuck_phases(store: Any) -> List[str]:
    """Fail jobs stuck the CARD-530 way; return their ids."""
    lister = getattr(store, "list_jobs_by_status", None)
    if not callable(lister):
        return []
    orch = JobPhaseOrchestrator(store)
    fixed: List[str] = []
    for job in lister("running") or []:
        phase_id = getattr(job, "current_phase_id", None)
        if not phase_id:
            continue
        try:
            phase = store.get_phase(phase_id)
        except Exception:  # noqa: BLE001 - a missing phase is not this repair's business
            continue
        if phase.status != PhaseStatus.QUEUED or _react_value(phase) != "DONE":
            continue
        orch.fail_phase(phase.id, STUCK_PHASE_REASON)
        save = getattr(store, "save_standing_journey_event", None)
        if callable(save):
            try:
                save(
                    job_id=job.id,
                    kind="reconciled_stuck_phase",
                    payload={"phase_id": phase.id, "phase_name": phase.name, "reason": STUCK_PHASE_REASON},
                )
            except Exception:  # noqa: BLE001
                logger.debug("journey event for %s skipped", job.id)
        logger.warning("Repaired stuck job %s: phase %s queued/DONE -> failed [CARD-530]", job.id, phase.id)
        fixed.append(job.id)
    return fixed
