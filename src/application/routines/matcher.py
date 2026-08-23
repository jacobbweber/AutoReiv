"""
Schedule Matcher & Due Date Calculator for Routines [REQ-ROUTINE-003].
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from src.domain.routines.models import Routine, ScheduleType


class ScheduleMatcher:
    """
    Evaluates whether routines are due for execution based on interval or cron schedules.
    """

    @classmethod
    def is_routine_due(
        cls,
        routine: Routine,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """Check if a routine is ready to be executed."""
        if not routine.enabled:
            return False

        now = current_time or datetime.now(timezone.utc)

        if routine.last_run_at is None:
            return True

        if routine.schedule_type == ScheduleType.INTERVAL:
            elapsed = (now - routine.last_run_at).total_seconds()
            return elapsed >= routine.interval_seconds

        if routine.schedule_type == ScheduleType.CRON:
            if routine.next_run_at is not None:
                return now >= routine.next_run_at
            # Fallback to interval calculation
            elapsed = (now - routine.last_run_at).total_seconds()
            return elapsed >= (routine.interval_seconds or 3600)

        return False

    @classmethod
    def compute_next_run(
        cls,
        routine: Routine,
        base_time: Optional[datetime] = None,
    ) -> datetime:
        """Calculate the next execution timestamp."""
        now = base_time or datetime.now(timezone.utc)

        if routine.schedule_type == ScheduleType.INTERVAL:
            return now + timedelta(seconds=routine.interval_seconds)

        # Fallback for cron/general
        return now + timedelta(seconds=routine.interval_seconds or 3600)
