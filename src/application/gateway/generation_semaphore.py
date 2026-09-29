"""
Process-global Ollama generation semaphore [REQ-ORCH-038].

Policy:
- Extra generations QUEUE behind the semaphore (serial handoffs work).
- A parallel batch that requests more children than the cap ERRORS.
  It is not silent-truncated.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque, Optional

DEFAULT_MAX_CONCURRENT_GENERATIONS = 1
MIN_MAX_CONCURRENT_GENERATIONS = 1
MAX_MAX_CONCURRENT_GENERATIONS = 3


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
