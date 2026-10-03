"""
Generation slot limits [REQ-ORCH-038]; one pool per provider endpoint plus a background pool [CARD-585].

Policy:
- Extra generations QUEUE behind the semaphore (serial handoffs work).
- A parallel batch that requests more children than the cap ERRORS.
  It is not silent-truncated.
"""

from __future__ import annotations

import asyncio
import contextvars
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional
from urllib.parse import urlsplit

DEFAULT_MAX_CONCURRENT_GENERATIONS = 1
MIN_MAX_CONCURRENT_GENERATIONS = 1
MAX_MAX_CONCURRENT_GENERATIONS = 3
BACKGROUND_POOL = "background"
BACKGROUND_MAX_CONCURRENT_GENERATIONS = 1


# CARD-494: set by a chat stream worker; called with ("queued", {...}) when its model call has to wait for a slot
# and ("dequeued", {}) when it gets one. Contextvars stay with the worker task, so other chats are not told.
slot_wait_listener: contextvars.ContextVar[Optional[Callable[[str, Dict[str, Any]], None]]] = contextvars.ContextVar(
    "slot_wait_listener", default=None
)
SLOT_WAIT_REASON = "another reply is running"


class HandoffBatchExceedsCapError(ValueError):
    """Batch size greater than max_concurrent_generations; nothing was dropped."""


def clamp_max_concurrent_generations(value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_concurrent_generations must be an integer from 1 to 3.") from exc
    if parsed < MIN_MAX_CONCURRENT_GENERATIONS or parsed > MAX_MAX_CONCURRENT_GENERATIONS:
        raise ValueError(
            f"max_concurrent_generations must be {MIN_MAX_CONCURRENT_GENERATIONS}-"
            f"{MAX_MAX_CONCURRENT_GENERATIONS}, got {parsed}."
        )
    return parsed


def validate_handoff_batch(batch_size: int, max_concurrent: Optional[int] = None) -> None:
    """Fail closed if a handoff batch asks for more concurrent children than the cap."""
    cap = get_process_generation_limit() if max_concurrent is None else clamp_max_concurrent_generations(max_concurrent)
    size = int(batch_size)
    if size > cap:
        raise HandoffBatchExceedsCapError(
            f"Handoff batch size {size} exceeds max_concurrent_generations={cap}. "
            "Reduce the batch or raise the cap (1-3). The batch was not truncated."
        )


_process_limit = DEFAULT_MAX_CONCURRENT_GENERATIONS


def get_process_generation_limit() -> int:
    return _process_limit


def configure_process_generation_limit(value: int) -> int:
    """Set the process-wide cap used for batch checks and default gateway semaphores."""
    global _process_limit
    _process_limit = clamp_max_concurrent_generations(value)
    return _process_limit


class GenerationSemaphore:
    """Counting slot limiter. Extra acquire() calls wait in queue; they do not error.

    CARD-579: the cap can change while generations run or wait (Settings > max concurrent generations).
    The old version swapped in a new asyncio.Semaphore, so a reply queued on the old one waited forever and
    releases went to the wrong semaphore. Here one counter and one queue survive a cap change: a raised
    cap starts queued generations at once, a lowered cap applies as running ones finish.
    """

    def __init__(self, max_concurrent: int = DEFAULT_MAX_CONCURRENT_GENERATIONS):
        self._max = clamp_max_concurrent_generations(max_concurrent)
        self._in_use = 0
        self._waiters: Deque[asyncio.Future] = deque()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def max_concurrent(self) -> int:
        return self._max

    @property
    def in_use(self) -> int:
        return self._in_use

    @property
    def waiting(self) -> int:
        return sum(1 for f in self._waiters if not f.done())

    def would_wait(self) -> bool:
        """CARD-494: True when an acquire now would queue (every slot taken, or others already waiting)."""
        return self._in_use >= self._max or self.waiting > 0

    def set_max_concurrent(self, max_concurrent: int) -> None:
        self._max = clamp_max_concurrent_generations(max_concurrent)
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            self._wake()
        else:  # a sync settings route runs in a worker thread
            loop.call_soon_threadsafe(self._wake)

    def _wake(self) -> None:
        while self._waiters and self._in_use < self._max:
            fut = self._waiters.popleft()
            if fut.done():
                continue
            self._in_use += 1  # the slot is handed straight to the waiter
            fut.set_result(True)

    def _release(self) -> None:
        self._in_use = max(0, self._in_use - 1)
        self._wake()

    def validate_batch_size(self, batch_size: int) -> None:
        validate_handoff_batch(batch_size, self._max)

    async def __aenter__(self) -> "GenerationSemaphore":
        if self._in_use < self._max and not any(not f.done() for f in self._waiters):
            self._in_use += 1
            return self
        loop = asyncio.get_running_loop()
        self._loop = loop
        fut = loop.create_future()
        self._waiters.append(fut)
        try:
            await fut
        except asyncio.CancelledError:
            if fut.done() and not fut.cancelled():
                self._release()  # a slot was handed over just as we were cancelled: give it back
            else:
                try:
                    self._waiters.remove(fut)
                except ValueError:
                    pass
            raise
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self._release()
        return False


def provider_pool_key(provider: Any) -> str:
    """CARD-585: the slot pool a provider uses: its endpoint (host:port), else its provider id.

    Two adapters that point at the same server (the default vLLM provider and an agent override on the same
    gateway) share one pool; Spark and Nimo get separate pools.
    """
    base = str(getattr(provider, "base_url", "") or "").strip()
    if base:
        parts = urlsplit(base if "://" in base else f"http://{base}")
        host = (parts.hostname or "").lower()
        if host in ("localhost", "::1", "0.0.0.0"):
            host = "127.0.0.1"
        if host:
            try:
                port = parts.port
            except ValueError:
                port = None
            port = port or (443 if parts.scheme == "https" else 80)
            return f"{host}:{port}"
    return f"provider:{getattr(provider, 'provider_id', None) or 'unknown'}"


class GenerationPools:
    """CARD-585: one slot pool per provider endpoint plus one pool for background calls.

    Before this, one process-wide pool covered every provider, so slow Spark turns held the slots and a Developer turn
    on Nimo waited minutes before its model was even called. Each provider pool gets the Settings cap
    (max_concurrent_generations, 1-3); background calls (memory extraction, capability detection, Teach and Studio
    helpers) use their own small pool so they never hold a chat reply's slot.
    """

    def __init__(
        self,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT_GENERATIONS,
        background_max: int = BACKGROUND_MAX_CONCURRENT_GENERATIONS,
    ):
        self._max = clamp_max_concurrent_generations(max_concurrent)
        self._pools: Dict[str, GenerationSemaphore] = {}
        self._background = GenerationSemaphore(background_max)

    @property
    def max_concurrent(self) -> int:
        return self._max

    @property
    def background(self) -> GenerationSemaphore:
        return self._background

    def set_max_concurrent(self, max_concurrent: int) -> int:
        self._max = clamp_max_concurrent_generations(max_concurrent)
        for pool in self._pools.values():
            pool.set_max_concurrent(self._max)
        return self._max

    def pool(self, key: str) -> GenerationSemaphore:
        sem = self._pools.get(key)
        if sem is None:
            sem = GenerationSemaphore(self._max)
            self._pools[key] = sem
        return sem

    def snapshot(self) -> Dict[str, Dict[str, int]]:
        out = {k: {"max": s.max_concurrent, "in_use": s.in_use, "waiting": s.waiting} for k, s in self._pools.items()}
        bg = self._background
        out[BACKGROUND_POOL] = {"max": bg.max_concurrent, "in_use": bg.in_use, "waiting": bg.waiting}
        return out
