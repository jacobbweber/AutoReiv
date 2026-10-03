"""Kill / resume mid-LLM helpers [CARD-259 / REQ-KILLR-*].

Operator abort during a standing phase LLM is a durable checkpoint, not a
Job death. Resume continues the same job_id (CARD-219 path). Never fail_phase
or cancel just because the worker was cancelled.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

OPERATOR_KILL_REASON = "operator_kill_mid_llm"
SERVER_RESTART_REASON = "server_restart"  # CARD-609: a restart cut the phase off; resumable like Stop
KILL_CHECKPOINTED = "kill_checkpointed"
WAITING_FOR_ANSWER_REASON = "waiting_for_answer"  # CARD-613: the step asked Jacob a question; his reply continues it


def is_operator_kill_reason(reason: Any) -> bool:
    text = str(reason or "").strip().lower()
    if not text:
        return False
    return (
        text == OPERATOR_KILL_REASON
        or text == SERVER_RESTART_REASON
        or text.startswith("operator_kill")
        or KILL_CHECKPOINTED in text
    )


def _status(value: Any) -> str:
    return str(getattr(value, "value", value) or "").lower()


def _paused_reason(store: Any, job: Any, phases: Optional[list]) -> Optional[str]:
    """The latest checkpoint's reason for an open job with nothing running or parked and a phase queued, else None."""
    if _status(getattr(job, "status", "")) not in ("running", "in_progress"):
        return None
    if phases is None:
        lister = getattr(store, "list_phases_for_job", None)
        phases = list(lister(job.id) or []) if callable(lister) else []
    states = {_status(getattr(p, "status", "")) for p in phases}
    if "queued" not in states or states & {"running", "in_progress", "waiting_approval"}:
        return None
    getter = getattr(store, "get_latest_job_phase_checkpoint", None)
    if not callable(getter):
        return None
    try:
        checkpoint = getter(job.id)
    except Exception:  # noqa: BLE001 - no checkpoint means not resumable from here
        return None
    return str(getattr(checkpoint, "last_fail_reason", "") or "") if checkpoint is not None else None


def job_left_parked(store: Any, job: Any) -> bool:
    """CARD-613: parked on an approval card (park_phase) with no pending approval left: the card was decided (e.g.
    through the API) but nothing resumed the job. Resume continues it. A verify-gate park is not this."""
    if _status(getattr(job, "status", "")) != "waiting_approval":
        return False
    pending = getattr(store, "get_pending_approvals", None)
    getter = getattr(store, "get_latest_job_phase_checkpoint", None)
    sid = str(getattr(job, "session_id", "") or "")
    if not callable(pending) or not callable(getter) or not sid:
        return False
    try:
        checkpoint = getter(job.id)
        return bool(checkpoint is not None and checkpoint.hitl_park_state and not pending(session_id=sid))
    except Exception:  # noqa: BLE001 - unknown means not stopped
        return False


def job_stopped_by_operator(store: Any, job: Any, phases: Optional[list] = None) -> bool:
    """CARD-490: an open job that Stop (or, CARD-609, a server restart) paused: nothing running or parked, a
    phase queued, and the latest checkpoint was written by that kill. Resume (``resume: true``) continues it.
    CARD-613: also a job left parked after its approval was decided without a resume."""
    if job_left_parked(store, job):
        return True
    return is_operator_kill_reason(_paused_reason(store, job, phases))


def job_waiting_for_answer(store: Any, job: Any, phases: Optional[list] = None) -> bool:
    """CARD-613: the job's step ended with a question for Jacob; his next chat message continues that step."""
    return _paused_reason(store, job, phases) == WAITING_FOR_ANSWER_REASON


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
