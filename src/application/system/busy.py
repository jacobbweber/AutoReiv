"""
Busy-state detection for software-update deferral [CARD-451 REQ-451-015].

Busy = active chat streams, running routines, or Studio/Factory jobs in
queued / running / waiting_approval.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

_ACTIVE_JOB_STATUSES = frozenset({"queued", "running", "waiting_approval"})


class BusyDetector:
    """Composable busy checker; callables are injectable for tests."""

    def __init__(
        self,
        *,
        chat_stream_checker: Optional[Callable[[], bool]] = None,
        routine_checker: Optional[Callable[[], bool]] = None,
        studio_job_checker: Optional[Callable[[], bool]] = None,
        factory_job_checker: Optional[Callable[[], bool]] = None,
    ) -> None:
        self._chat_stream_checker = chat_stream_checker or _default_chat_streams_busy
        self._routine_checker = routine_checker or (lambda: False)
        self._studio_job_checker = studio_job_checker or (lambda: False)
        self._factory_job_checker = factory_job_checker or (lambda: False)

    def is_busy(self) -> Tuple[bool, str]:
        reasons: List[str] = []
        try:
            if self._chat_stream_checker():
                reasons.append("active chat stream")
        except Exception as exc:
            logger.debug("chat busy check failed: %s", exc)
        try:
            if self._routine_checker():
                reasons.append("running routine")
        except Exception as exc:
            logger.debug("routine busy check failed: %s", exc)
        try:
            if self._studio_job_checker():
                reasons.append("running Studio job")
        except Exception as exc:
            logger.debug("studio job busy check failed: %s", exc)
        try:
            if self._factory_job_checker():
                reasons.append("running Factory/training job")
        except Exception as exc:
            logger.debug("factory job busy check failed: %s", exc)
        if reasons:
            return True, ", ".join(reasons)
        return False, ""


def _default_chat_streams_busy() -> bool:
    try:
        from src.web.routers import chat as chat_mod

        tasks = getattr(chat_mod, "_active_stream_tasks", {}) or {}
        for task in list(tasks.values()):
            if task is None:
                continue
            done = getattr(task, "done", None)
            if callable(done):
                if not done():
                    return True
            else:
                return True
    except Exception:
        return False
    return False


def make_store_busy_detector(store: Any, factory_repo: Any = None) -> BusyDetector:
    """Build a BusyDetector wired to SQLiteStateStore (+ optional Factory repo)."""

    def routines_busy() -> bool:
        if store is None:
            return False
        try:
            routines = store.list_routines(enabled_only=False) if hasattr(store, "list_routines") else []
            for r in routines or []:
                status = getattr(r, "last_status", None)
                val = getattr(status, "value", status)
                if str(val).lower() == "running":
                    return True
            if hasattr(store, "get_routine_runs"):
                for run in store.get_routine_runs(limit=20) or []:
                    status = getattr(run, "status", None)
                    val = getattr(status, "value", status)
                    if str(val).lower() == "running":
                        return True
        except Exception as exc:
            logger.debug("routine busy scan failed: %s", exc)
        return False

    def studio_jobs_busy() -> bool:
        if store is None or not hasattr(store, "_get_connection"):
            return False
        try:
            conn = store._get_connection()
            try:
                cur = conn.execute(
                    "SELECT COUNT(1) AS c FROM jobs WHERE lower(status) IN ('queued','running','waiting_approval')"
                )
                row = cur.fetchone()
                count = int(row["c"] if row and "c" in row.keys() else (row[0] if row else 0))
                return count > 0
            finally:
                if getattr(store, "_mem_conn", None) is None:
                    conn.close()
        except Exception as exc:
            logger.debug("studio jobs busy scan failed: %s", exc)
            return False

    def factory_jobs_busy() -> bool:
        repo = factory_repo
        if repo is None:
            return False
        try:
            jobs = repo.list_jobs() if hasattr(repo, "list_jobs") else []
            for j in jobs or []:
                st = str(getattr(j, "status", "")).lower()
                if st in _ACTIVE_JOB_STATUSES:
                    return True
        except Exception as exc:
            logger.debug("factory jobs busy scan failed: %s", exc)
        return False

    return BusyDetector(
        chat_stream_checker=_default_chat_streams_busy,
        routine_checker=routines_busy,
        studio_job_checker=studio_jobs_busy,
        factory_job_checker=factory_jobs_busy,
    )
