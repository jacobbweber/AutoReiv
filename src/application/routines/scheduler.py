"""
Routine Scheduler & Background Execution Loop [REQ-ROUTINE-003, REQ-ROUTINE-004].
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

from src.application.routines.executor import RoutineExecutor
from src.application.routines.matcher import ScheduleMatcher
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.domain.routines.models import RoutineRun
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


class RoutineScheduler:
    """
    Background scheduler that periodically checks routine due times
    and triggers autonomous agent executions.
    """

    def __init__(
        self,
        executor: RoutineExecutor,
        state_store: SQLiteStateStore,
        tick_interval_seconds: float = 10.0,
    ):
        self.executor = executor
        self.state_store = state_store
        self.tick_interval_seconds = tick_interval_seconds
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def skip_missed_runs(self, now: Optional[datetime] = None, *, reason: str = "on tick") -> List[str]:
        """
        Move every enabled routine with no next run, or a slot past the grace window,
        to its next scheduled time without running it [CARD-635]. Returns skipped ids.
        """
        now = now or datetime.now(timezone.utc)
        skipped: List[str] = []
        for routine in self.state_store.list_routines(enabled_only=True):
            if not ScheduleMatcher.needs_reschedule(routine, now):
                continue
            was = routine.next_run_at
            routine.next_run_at = ScheduleMatcher.compute_next_run(routine, base_time=now)
            self.state_store.save_routine(routine)
            if was is None:
                logger.info(
                    "Routine '%s' had no next run; scheduled for %s (%s).",
                    routine.id, routine.next_run_at.isoformat(), reason,
                )
            else:
                skipped.append(routine.id)
                logger.info(
                    "Routine '%s' skipped missed run due %s (%s); next run %s.",
                    routine.id, was.isoformat(), reason, routine.next_run_at.isoformat(),
                )
        return skipped

    async def tick(self) -> List[RoutineRun]:
        """
        Skip missed runs, then execute enabled routines whose slot is now [CARD-635].
        """
        self.skip_missed_runs(reason="on tick")
        enabled_routines = self.state_store.list_routines(enabled_only=True)
        executed_runs: List[RoutineRun] = []

        for routine in enabled_routines:
            if ScheduleMatcher.is_routine_due(routine):
                try:
                    run = await self.executor.execute_routine(routine)
                    executed_runs.append(run)
                except Exception as e:
                    logger.error(f"Error executing routine '{routine.id}': {e}", exc_info=True)

        return executed_runs

    async def start(self) -> None:
        """
        Run the background scheduler loop until stopped.
        """
        self._running = True
        logger.info("RoutineScheduler started.")
        try:
            # CARD-635: nothing fires because the app started; missed slots move to the next time.
            self.skip_missed_runs(reason="at start")
        except Exception as e:
            logger.error(f"Error skipping missed runs at start: {e}", exc_info=True)
        while self._running:
            try:
                await self.tick()
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}", exc_info=True)

            await asyncio.sleep(self.tick_interval_seconds)

    async def stop(self) -> None:
        """
        Stop the background scheduler loop.
        """
        self._running = False
        logger.info("RoutineScheduler stopped.")

    @classmethod
    def seed_default_routines(cls, store: SQLiteStateStore) -> None:
        """
        Seed the standard Day-1 agent routines into the database if not present.
        """
        for r in BUILTIN_ROUTINES:
            existing = store.get_routine(r.id) if hasattr(store, "get_routine") else None
            if not existing:
                if r.next_run_at is None:
                    r.next_run_at = ScheduleMatcher.compute_next_run(r)
                store.save_routine(r)
            else:
                updated = False
                if existing.agent_id in ("assistant", "wiki", "agent-builder"):
                    existing.agent_id = r.agent_id
                    updated = True
                if existing.next_run_at is None and existing.last_run_at is None:
                    existing.next_run_at = ScheduleMatcher.compute_next_run(existing)
                    updated = True
                if updated:
                    store.save_routine(existing)
        if getattr(store, "set_setting", None):
            store.set_setting("day1_routines_seeded", True)
