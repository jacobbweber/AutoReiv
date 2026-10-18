"""
Active chat stream tracking, SSE heartbeat keepalives, and turn side-task lifecycle [CARD-713].

Lives in src/application/chat/ so application-layer services (such as BusyDetector)
can inspect active chat streams without importing upward from src/web/.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

SSE_KEEPALIVE_SECONDS = 15.0  # CARD-592: chat stream heartbeat
SSE_KEEPALIVE = ": keepalive\n\n"

# Active background generation tasks by session_id [REQ-RESIL-003, CARD-114 Finding 4]
_active_stream_tasks: Dict[str, asyncio.Task] = {}
_active_stream_agents: Dict[str, str] = {}
# CARD-491: background tasks a chat turn started (memory extraction), by session, with the worker that started them.
_turn_side_tasks: Dict[str, List[tuple]] = {}


async def sse_with_keepalive(
    queue: "asyncio.Queue[Optional[str]]",
    interval: Optional[float] = None,
) -> AsyncGenerator[str, None]:
    """Yield queued SSE items until None; while nothing arrives, an SSE comment every ``interval`` seconds.

    CARD-592: the model may think, a tool or an approval may run for many minutes, so proxies and browsers never see
    an idle connection. Clients skip lines that are not "data:".
    """
    wait = interval if interval is not None else SSE_KEEPALIVE_SECONDS
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=wait)
        except asyncio.TimeoutError:
            yield SSE_KEEPALIVE
            continue
        if item is None:
            return
        yield item


def spawn_turn_side_task(session_id: str, coro: Any) -> asyncio.Task:
    """Start a background task for this chat turn; Stop on the turn cancels it [CARD-491 REQ-491-001]."""
    owner = asyncio.current_task()
    task = asyncio.create_task(coro)
    entries = _turn_side_tasks.setdefault(session_id, [])
    entries.append((owner, task))

    def _forget(done: asyncio.Task) -> None:
        left = [e for e in _turn_side_tasks.get(session_id, []) if e[1] is not done]
        if left:
            _turn_side_tasks[session_id] = left
        else:
            _turn_side_tasks.pop(session_id, None)

    task.add_done_callback(_forget)
    return task


def cancel_turn_side_tasks(session_id: str, owner: Optional[asyncio.Task]) -> int:
    """Cancel the unfinished background tasks ``owner`` (a stopped worker) started. Returns how many."""
    n = 0
    for own, task in list(_turn_side_tasks.get(session_id, [])):
        if own is owner and not task.done():
            task.cancel()
            n += 1
    return n


def session_turn_running(session_id: str) -> bool:
    """True while a chat worker for ``session_id`` is still running [CARD-530 REQ-530-003]."""
    task = _active_stream_tasks.get(session_id)
    return bool(task is not None and not task.done())


def live_stream_session_ids() -> List[str]:
    """Return session IDs with an active in-flight chat stream worker."""
    return [sid for sid, task in list(_active_stream_tasks.items()) if task is not None and not task.done()]


def has_active_chat_streams() -> bool:
    """Return True if any chat stream task is currently running [CARD-451, CARD-713]."""
    for task in list(_active_stream_tasks.values()):
        if task is None:
            continue
        done = getattr(task, "done", None)
        if callable(done):
            if not done():
                return True
        else:
            return True
    return False
