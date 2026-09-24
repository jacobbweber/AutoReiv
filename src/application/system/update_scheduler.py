"""
Daily software-update scheduler [CARD-451 REQ-451-007, REQ-451-013, REQ-451-015].

Patterned on DataDirBackupScheduler: periodic tick, due-time check, busy deferral
with bounded retries.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 60.0
MAX_DEFER_RETRIES_PER_DAY = 48  # e.g. every 15 min for 12h if interval is shorter externally


class SoftwareUpdateScheduler:
    """Background worker that runs daily auto-update when due and idle."""

    def __init__(
        self,
        update_service: Any,
        *,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        self.update_service = update_service
        self.interval_seconds = interval_seconds
        self._running = False
        self._defer_count_date: Optional[str] = None
        self._defer_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    async def tick(self, now: Optional[datetime] = None) -> Optional[Any]:
        if self.update_service is None:
            return None
        current = now or datetime.now().astimezone()
        day_key = current.date().isoformat()
        if self._defer_count_date != day_key:
            self._defer_count_date = day_key
            self._defer_count = 0

        try:
            result = self.update_service.run_auto_update_if_due(now=current)
        except Exception as exc:
            logger.error("SoftwareUpdateScheduler tick failed: %s", exc, exc_info=True)
            return None

        if result is None:
            return None

        if getattr(result, "refused", False) and "busy" in (getattr(result, "message", "") or "").lower():
            self._defer_count += 1
            if self._defer_count > MAX_DEFER_RETRIES_PER_DAY:
                logger.warning(
                    "Auto-update deferred %d times today; giving up until tomorrow",
                    self._defer_count,
                )
            return result

        return result

    async def start(self) -> None:
        self._running = True
        logger.info("SoftwareUpdateScheduler started (interval: %.1fs)", self.interval_seconds)
        while self._running:
            try:
                await self.tick()
            except Exception as exc:
                logger.error("Error in SoftwareUpdateScheduler tick: %s", exc, exc_info=True)
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
        self._running = False
        logger.info("SoftwareUpdateScheduler stopped")

    async def stop(self) -> None:
        self._running = False
