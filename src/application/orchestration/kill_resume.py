"""Kill / resume mid-LLM helpers [CARD-259 / REQ-KILLR-*].

Operator abort during a standing phase LLM is a durable checkpoint, not a
Job death. Resume continues the same job_id (CARD-219 path). Never fail_phase
or cancel just because the worker was cancelled.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

OPERATOR_KILL_REASON = "operator_kill_mid_llm"
KILL_CHECKPOINTED = "kill_checkpointed"


def is_operator_kill_reason(reason: Any) -> bool:
    text = str(reason or "").strip().lower()
    if not text:
        return False
    return (
        text == OPERATOR_KILL_REASON
        or text.startswith("operator_kill")
        or KILL_CHECKPOINTED in text
    )


def _status(value: Any) -> str:
    return str(getattr(value, "value", value) or "").lower()


def job_stopped_by_operator(store: Any, job: Any, phases: Optional[list] = None) -> bool:
    """CARD-490: an open job that Stop paused: nothing running or parked, a phase queued, and the latest
    checkpoint was written by an operator kill. Resume (``resume: true``) continues it."""
    if _status(getattr(job, "status", "")) not in ("running", "in_progress"):
        return False
    if phases is None:
        lister = getattr(store, "list_phases_for_job", None)
        phases = list(lister(job.id) or []) if callable(lister) else []
    states = {_status(getattr(p, "status", "")) for p in phases}
    if "queued" not in states or states & {"running", "in_progress", "waiting_approval"}:
        return False
    getter = getattr(store, "get_latest_job_phase_checkpoint", None)
    if not callable(getter):
        return False
    try:
        checkpoint = getter(job.id)
    except Exception:  # noqa: BLE001 - no checkpoint means not resumable from here
        return False
    return bool(checkpoint is not None and is_operator_kill_reason(getattr(checkpoint, "last_fail_reason", "")))


def kill_checkpoint_payload(
    *,
    job_id: Optional[str] = None,
    phase_id: Optional[str] = None,
    phase_name: Optional[str] = None,
    checkpointed: bool = False,
    resumable: bool = True,
    reason: str = OPERATOR_KILL_REASON,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "checkpointed": bool(checkpointed),
        "resumable": bool(resumable),
        "job_id": job_id,
        "phase_id": phase_id,
        "phase_name": phase_name,
        "reason": reason,
        "status": "aborted",
        "event": KILL_CHECKPOINTED,
    }
    if extra:
        payload.update(extra)
    return payload
