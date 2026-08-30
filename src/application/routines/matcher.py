"""
Schedule Matcher & Due Date Calculator for Routines [REQ-ROUTINE-003] [REQ-IMPROVE-008].
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from src.domain.routines.models import Routine, ScheduleType


def _try_zoneinfo(name: str):
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        return None


def _first_sunday(year: int, month: int) -> date:
    first = date(year, month, 1)
    return date(year, month, 1 + (6 - first.weekday()) % 7)


def _second_sunday(year: int, month: int) -> date:
    return _first_sunday(year, month) + timedelta(days=7)


def _eastern_offset_hours(local_date: date) -> int:
    """US DST since 2007: 2nd Sunday March -> 1st Sunday November. 21:00 is never near 02:00."""
    start = _second_sunday(local_date.year, 3)
    end = _first_sunday(local_date.year, 11)
    if start <= local_date < end:
        return -4
    return -5


def to_local(utc: datetime, tz_name: str) -> datetime:
    aware = utc if utc.tzinfo else utc.replace(tzinfo=timezone.utc)
    zi = _try_zoneinfo(tz_name)
    if zi is not None:
        return aware.astimezone(zi)
    if tz_name in {"America/New_York", "US/Eastern"}:
        for guess in (-4, -5):
            local = aware.astimezone(timezone(timedelta(hours=guess)))
            if _eastern_offset_hours(local.date()) == guess:
                return local
        return aware.astimezone(timezone(timedelta(hours=-4)))
    return aware


def from_local_civil(local_civil: datetime, tz_name: str) -> datetime:
    """Interpret a naive civil time in tz_name and return the UTC instant."""
    naive = local_civil.replace(tzinfo=None)
    zi = _try_zoneinfo(tz_name)
    if zi is not None:
        return naive.replace(tzinfo=zi).astimezone(timezone.utc)
    if tz_name in {"America/New_York", "US/Eastern"}:
        hours = _eastern_offset_hours(naive.date())
        label = "EDT" if hours == -4 else "EST"
        return naive.replace(tzinfo=timezone(timedelta(hours=hours), name=label)).astimezone(timezone.utc)
    return naive.replace(tzinfo=timezone.utc)


def uses_local_clock(routine: Routine) -> bool:
    meta = routine.metadata or {}
    if str(meta.get("timezone") or "").strip():
        return True
    if meta.get("weekdays_only"):
        return True
    return meta.get("hour") is not None


def compute_next_local_weekday_run(
    routine: Routine,
    base_time: datetime,
    *,
    inclusive: bool = False,
) -> datetime:
    """
    Next weekday local_time in routine.metadata timezone, stored as UTC.

    CARD-111: 02:00 America/New_York is the wrong default (surprise GPU load).
    21:00 UTC is 17:00 EDT -- also wrong. Do not treat cron as UTC.
    """
    meta = routine.metadata or {}
    tz_name = str(meta.get("timezone") or "America/New_York").strip() or "America/New_York"
    hour = int(meta.get("hour", 21))
    minute = int(meta.get("minute", 0))
    weekdays_only = bool(meta.get("weekdays_only", True))
    now = base_time if base_time.tzinfo else base_time.replace(tzinfo=timezone.utc)
    local_now = to_local(now, tz_name)
    cand = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    past = local_now > cand if inclusive else local_now >= cand
    if past:
        cand = cand + timedelta(days=1)
    if weekdays_only:
        while cand.weekday() >= 5:
            cand = cand + timedelta(days=1)
    return from_local_civil(cand, tz_name)


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
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if routine.next_run_at is not None:
            nxt = routine.next_run_at
            if nxt.tzinfo is None:
                nxt = nxt.replace(tzinfo=timezone.utc)
            return now >= nxt

        if uses_local_clock(routine):
            slot = compute_next_local_weekday_run(routine, now, inclusive=True)
            return now >= slot

        if routine.last_run_at is None:
            return True

        if routine.schedule_type == ScheduleType.INTERVAL:
            elapsed = (now - routine.last_run_at).total_seconds()
            return elapsed >= routine.interval_seconds

        if routine.schedule_type == ScheduleType.CRON:
            elapsed = (now - routine.last_run_at).total_seconds()
            return elapsed >= (routine.interval_seconds or 3600)

        return False

    @classmethod
    def compute_next_run(
        cls,
        routine: Routine,
        base_time: Optional[datetime] = None,
    ) -> datetime:
        """Calculate the next execution timestamp (UTC instant)."""
        now = base_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if uses_local_clock(routine):
            return compute_next_local_weekday_run(routine, now, inclusive=False)

        if routine.schedule_type == ScheduleType.INTERVAL:
            return now + timedelta(seconds=routine.interval_seconds)

        return now + timedelta(seconds=routine.interval_seconds or 3600)
