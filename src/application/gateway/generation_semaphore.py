"""
Process-global Ollama generation semaphore [REQ-ORCH-038].

Policy:
- Extra generations QUEUE behind the semaphore (serial handoffs work).
- A parallel batch that requests more children than the cap ERRORS.
  It is not silent-truncated.
"""

from __future__ import annotations

import asyncio
from typing import Optional

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
    """asyncio.Semaphore wrapper. Extra acquire() calls wait in queue; they do not error."""

    def __init__(self, max_concurrent: int = DEFAULT_MAX_CONCURRENT_GENERATIONS):
        self._max = clamp_max_concurrent_generations(max_concurrent)
        self._sem = asyncio.Semaphore(self._max)

    @property
    def max_concurrent(self) -> int:
        return self._max

    def set_max_concurrent(self, max_concurrent: int) -> None:
        new_max = clamp_max_concurrent_generations(max_concurrent)
        if new_max == self._max:
            return
        self._max = new_max
        self._sem = asyncio.Semaphore(new_max)

    def validate_batch_size(self, batch_size: int) -> None:
        validate_handoff_batch(batch_size, self._max)

    async def __aenter__(self) -> "GenerationSemaphore":
        await self._sem.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self._sem.release()
        return False
