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
