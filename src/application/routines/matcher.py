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




def get_schedule_rule(routine: Routine) -> Optional[dict]:
    """CARD-310: durable structured schedule in metadata.schedule_rule."""
    meta = routine.metadata or {}
    rule = meta.get("schedule_rule")
    return rule if isinstance(rule, dict) and rule else None


def schedule_rule_to_cron(rule: dict) -> Optional[str]:
    """Return a cron string when the rule is representable; else None (e.g. every N weeks > 1)."""
    if not rule:
        return None
    n = int(rule.get("every_n_weeks") or 1)
    if n > 1:
        return None
    hour = int(rule.get("hour", 0))
    minute = int(rule.get("minute", 0))
    months = rule.get("months")
    weekdays = rule.get("weekdays")
    doms = rule.get("days_of_month")

    def _field(vals, lo, hi):
        if not vals:
            return "*"
        cleaned = sorted({int(v) for v in vals if lo <= int(v) <= hi})
        if not cleaned:
            return "*"
        return ",".join(str(v) for v in cleaned)

    # cron DOW: 0=Sun..6=Sat; our UI/Python use Mon=0..Sun=6 → convert
    cron_dows = None
    if weekdays:
        cron_dows = []
        for w in weekdays:
            w = int(w)
            cron_dows.append(0 if w == 6 else w + 1)
    dow_f = _field(cron_dows, 0, 6) if cron_dows is not None else "*"
    dom_f = _field(doms, 1, 31) if doms else "*"
    mon_f = _field(months, 1, 12) if months else "*"
    # cron forbids both DOM and DOW constrained in some engines; allow both as OR-ish for preview only
    return f"{minute} {hour} {dom_f} {mon_f} {dow_f}"


def _rule_matches_local_day(rule: dict, local_dt: datetime) -> bool:
    months = rule.get("months")
    if months and int(local_dt.month) not in {int(m) for m in months}:
        return False
    weekdays = rule.get("weekdays")
    if weekdays is not None and len(weekdays) > 0:
        if int(local_dt.weekday()) not in {int(w) for w in weekdays}:
            return False
    doms = rule.get("days_of_month")
    if doms is not None and len(doms) > 0:
        if int(local_dt.day) not in {int(d) for d in doms}:
            return False
    n = int(rule.get("every_n_weeks") or 1)
    if n > 1:
        anchor = str(rule.get("anchor_date") or "").strip()
        if not anchor:
            return False
        try:
            ay, am, ad = (int(x) for x in anchor.split("-")[:3])
            anchor_d = date(ay, am, ad)
        except Exception:
            return False
        # Align to weeks since anchor Monday-based week index
        delta_days = (local_dt.date() - anchor_d).days
        if delta_days < 0:
            return False
        week_index = delta_days // 7
        if week_index % n != 0:
            return False
    return True


def compute_next_from_schedule_rule(
    rule: dict,
    base_time: datetime,
    *,
    inclusive: bool = False,
) -> datetime:
    """Next fire from structured schedule_rule (UTC instant)."""
    explicit_tz = str(rule.get("timezone") or "").strip()
    if not explicit_tz:
        from src.domain.routines.schedule_rule import compute_next_structured_run
        nxt = compute_next_structured_run(rule, base_time=base_time, inclusive=inclusive)
        if nxt is not None:
            return nxt

    tz_name = explicit_tz or "America/New_York"
    hour = int(rule.get("hour", 0))
    minute = int(rule.get("minute", 0))
    now = base_time if base_time.tzinfo else base_time.replace(tzinfo=timezone.utc)
    local_now = to_local(now, tz_name)
    start = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    past = local_now > start if inclusive else local_now >= start
    if past:
        start = start + timedelta(days=1)
        start = start.replace(hour=hour, minute=minute, second=0, microsecond=0)
    for _ in range(400):
        if _rule_matches_local_day(rule, start):
            return from_local_civil(start, tz_name)
        start = (start + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
    # fallback: one day later
    return from_local_civil(start, tz_name)


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

        rule = get_schedule_rule(routine)
        if rule is not None:
            slot = compute_next_from_schedule_rule(rule, now, inclusive=True)
            return now >= slot

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

        rule = get_schedule_rule(routine)
        if rule is not None:
            return compute_next_from_schedule_rule(rule, now, inclusive=False)

        if uses_local_clock(routine):
            return compute_next_local_weekday_run(routine, now, inclusive=False)

        if routine.schedule_type == ScheduleType.INTERVAL:
            return now + timedelta(seconds=routine.interval_seconds)

        return now + timedelta(seconds=routine.interval_seconds or 3600)
