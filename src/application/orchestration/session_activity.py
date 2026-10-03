"""CARD-493: which chats are replying or waiting for approval, for Recent Chats.

The same rule as ``GET /api/sessions/{id}/status`` (CARD-486): a chat is replying while its stream worker runs,
or while one of its jobs has a RUNNING phase (a Stop leaves the job open with its phase QUEUED; that is not
running). A chat needs approval while a pending approval belongs to it or to one of its hand-off / phase sessions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Set

logger = logging.getLogger(__name__)

PHASE_SESSION_MARKER = "::phase::"
_CHILD_MARKERS = ("_child_", PHASE_SESSION_MARKER)
OPEN_JOB_STATUSES = ("running", "in_progress")


def parent_session_id(session_id: Any) -> str:
    """The chat a hand-off or phase session belongs to (``<sid>_child_...`` / ``<sid>::phase::...``)."""
    sid = str(session_id or "")
    for marker in _CHILD_MARKERS:
        if marker in sid:
            sid = sid.split(marker, 1)[0]
    return sid


def is_job_step_session(session_id: Any) -> bool:
    """CARD-608: ``<sid>::phase::<phase id>`` is a job step's own transcript, not a chat."""
    return PHASE_SESSION_MARKER in str(session_id or "")


def _status(value: Any) -> str:
    return str(getattr(value, "value", value) or "").lower()


def job_has_running_phase(store: Any, job: Any) -> bool:
    """True when a phase of ``job`` is RUNNING. Stores without phase listing keep the old job-level answer."""
    if not hasattr(store, "list_phases_for_job"):
        return True
    return any(_status(p.status) == "running" for p in store.list_phases_for_job(job.id) or [])


def session_activity(store: Any, live_session_ids: Iterable[str] = ()) -> Dict[str, Set[str]]:
    """``{"running": {...}, "waiting_approval": {...}}`` chat ids. Soft-fails to what it could read."""
    running: Set[str] = {parent_session_id(s) for s in live_session_ids if s}
    waiting: Set[str] = set()
    lister = getattr(store, "list_jobs_by_status", None)
    if callable(lister):
        for status in OPEN_JOB_STATUSES:
            try:
                for job in lister(status) or []:
                    sid = getattr(job, "session_id", None)
                    if sid and job_has_running_phase(store, job):
                        running.add(parent_session_id(sid))
            except Exception:  # noqa: BLE001
                logger.debug("session_activity: job scan failed", exc_info=True)
    pending = getattr(store, "get_pending_approvals", None)
    if callable(pending):
        try:
            for row in pending() or []:
                sid = row.get("session_id") if isinstance(row, dict) else None
                if sid:
                    waiting.add(parent_session_id(sid))
        except Exception:  # noqa: BLE001
            logger.debug("session_activity: approval scan failed", exc_info=True)
    return {"running": running, "waiting_approval": waiting}
