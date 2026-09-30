"""CARD-593: work that follows an approval (a hand-off run, a parked child's resume) runs in the background.

The decision request returns at once with {"status": "running", "resume_id": ...}; the UI polls
GET /api/approvals/{id}/resume until the status is no longer "running". A phone that sleeps or a tab that closes
does not stop the work, and no client request has to stay open for minutes.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

RUNNING = "running"
KEEP_SECONDS = 6 * 3600  # finished entries are kept this long for late polls


class BackgroundResumes:
    def __init__(self, keep_seconds: float = KEEP_SECONDS):
        self._keep = keep_seconds
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    @staticmethod
    def poll_url(key: str) -> str:
        return f"/api/approvals/{key}/resume"

    def start(self, key: str, work: Callable[[], Awaitable[Optional[Dict[str, Any]]]]) -> Dict[str, Any]:
        """Start `work` on the running loop and return the running marker the decision response carries."""
        self._prune()
        entry: Dict[str, Any] = {"status": RUNNING, "resume_id": key, "started_at": time.time()}
        self._entries[key] = entry

        async def run() -> None:
            try:
                result = await work()
                entry.update(dict(result or {}))
                if entry.get("status") in (None, "", RUNNING):
                    entry["status"] = "completed"
            except Exception as exc:  # the poller must always see an end state
                logger.exception("Background resume %s failed", key)
                entry.update(status="failed", summary=str(exc) or type(exc).__name__)
            entry["finished_at"] = time.time()

        task = asyncio.get_running_loop().create_task(run())
        self._tasks[key] = task
        task.add_done_callback(lambda _t: self._tasks.pop(key, None))
        return {"status": RUNNING, "resume_id": key, "poll_url": self.poll_url(key)}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._entries.get(key)
        return dict(entry) if entry is not None else None

    async def wait(self, key: str) -> Optional[Dict[str, Any]]:
        """Tests and shutdown: wait for one entry to finish."""
        task = self._tasks.get(key)
        if task is not None:
            await asyncio.shield(task)
        return self.get(key)

    def _prune(self) -> None:
        cutoff = time.time() - self._keep
        for key in [k for k, e in self._entries.items() if e.get("finished_at") and e["finished_at"] < cutoff]:
            self._entries.pop(key, None)


def background_resumes(app_state: Any) -> BackgroundResumes:
    tracker = getattr(app_state, "background_resumes", None)
    if tracker is None:
        tracker = BackgroundResumes()
        app_state.background_resumes = tracker
    return tracker


def handoff_outcome(tool_res: Any) -> Dict[str, Any]:
    """Status for the poller from an approved hand-off tool's result."""
    output = getattr(tool_res, "output", None)
    if isinstance(output, dict) and output.get("status") == "approval_required":
        return {"status": "approval_required", "summary": str(output.get("message") or "Approval required")}
    if not getattr(tool_res, "success", False):
        return {"status": "failed", "summary": str(getattr(tool_res, "error", "") or "Hand-off failed")}
    text = output if isinstance(output, str) else str(output)
    if "Handoff Failed" in text:
        return {"status": "failed", "summary": text[:600]}
    return {"status": "completed", "summary": text[:600]}
