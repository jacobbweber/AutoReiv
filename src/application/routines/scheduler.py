"""
Routine Scheduler & Background Execution Loop [REQ-ROUTINE-003, REQ-ROUTINE-004].
"""

import asyncio
import logging
from typing import List

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

    async def tick(self) -> List[RoutineRun]:
        """
        Evaluate all enabled routines and execute any that are due.
        """
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
            existing = store.get_routine(r.id)
            if not existing:
                store.save_routine(r)
