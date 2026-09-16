"""
Structured schedule rule helpers for Routines [CARD-310].

Persistence: rule lives in Routine.metadata["schedule_rule"] (no new SQL column).
API exposes it as top-level schedule_rule. Weekdays use cron convention: 0=Sun .. 6=Sat.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

SCHEDULE_RULE_KEY = "schedule_rule"


def _as_int_list(value: Any) -> Optional[List[int]]:
    if value is None:
        return None
    if isinstance(value, list):
        if len(value) == 0:
            return None
        out: List[int] = []
        for item in value:
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        return out or None
    return None


def normalize_schedule_rule(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize a schedule_rule dict; null/empty lists mean 'any' for that dimension."""
    raw = raw or {}
    hour = raw.get("hour", 0)
    minute = raw.get("minute", 0)
    try:
        hour_i = int(hour) if hour is not None else 0
    except (TypeError, ValueError):
        hour_i = 0
    try:
        minute_i = int(minute) if minute is not None else 0
    except (TypeError, ValueError):
        minute_i = 0
    hour_i = max(0, min(23, hour_i))
    minute_i = max(0, min(59, minute_i))

    every_n = raw.get("every_n_weeks", 1)
    try:
        every_n_i = int(every_n) if every_n is not None else 1
    except (TypeError, ValueError):
        every_n_i = 1
    if every_n_i < 1:
        every_n_i = 1

    anchor = raw.get("anchor_date")
    anchor_s = None
    if anchor:
        anchor_s = str(anchor).strip()[:10] or None
        if anchor_s:
            try:
                date.fromisoformat(anchor_s)
            except ValueError:
                anchor_s = None

    months = _as_int_list(raw.get("months"))
    weekdays = _as_int_list(raw.get("weekdays"))
    days_of_month = _as_int_list(raw.get("days_of_month"))
    if months:
        months = sorted({m for m in months if 1 <= m <= 12}) or None
    if weekdays:
        weekdays = sorted({d % 7 for d in weekdays if 0 <= int(d) <= 7}) or None
    if days_of_month:
        days_of_month = sorted({d for d in days_of_month if 1 <= d <= 31}) or None

    return {
        "months": months,
        "weekdays": weekdays,
        "days_of_month": days_of_month,
        "hour": hour_i,
        "minute": minute_i,
        "every_n_weeks": every_n_i,
        "anchor_date": anchor_s,
    }


def get_schedule_rule(routine_or_meta: Any) -> Optional[Dict[str, Any]]:
    """Read schedule_rule from a Routine or metadata dict."""
    meta = None
    if routine_or_meta is None:
        return None
    if isinstance(routine_or_meta, dict):
        meta = routine_or_meta
    else:
        meta = getattr(routine_or_meta, "metadata", None) or {}
    raw = meta.get(SCHEDULE_RULE_KEY) if isinstance(meta, dict) else None
    if not isinstance(raw, dict):
        return None
    return normalize_schedule_rule(raw)


def set_schedule_rule_on_metadata(metadata: Optional[Dict[str, Any]], rule: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    meta = dict(metadata or {})
    if rule is None:
        meta.pop(SCHEDULE_RULE_KEY, None)
    else:
        meta[SCHEDULE_RULE_KEY] = normalize_schedule_rule(rule)
    return meta


def cron_weekday(dt: datetime) -> int:
    """Python weekday Mon=0..Sun=6 → cron Sun=0..Sat=6."""
    return (dt.weekday() + 1) % 7


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _weeks_since_anchor(d: date, anchor: date) -> int:
    return (_monday_of(d) - _monday_of(anchor)).days // 7


def matches_every_n_weeks(d: date, every_n_weeks: int, anchor_date: Optional[str]) -> bool:
    if every_n_weeks is None or every_n_weeks <= 1:
        return True
    if not anchor_date:
        return True
    try:
        anchor = date.fromisoformat(anchor_date)
    except ValueError:
        return True
    weeks = _weeks_since_anchor(d, anchor)
    return weeks % every_n_weeks == 0


def civil_matches_rule(dt: datetime, rule: Dict[str, Any]) -> bool:
    """True if civil datetime matches all non-any dimensions of the rule."""
    rule = normalize_schedule_rule(rule)
    if rule["months"] is not None and dt.month not in rule["months"]:
        return False
    if rule["days_of_month"] is not None and dt.day not in rule["days_of_month"]:
        return False
    if rule["weekdays"] is not None and cron_weekday(dt) not in rule["weekdays"]:
        return False
    if dt.hour != rule["hour"] or dt.minute != rule["minute"]:
        return False
    if not matches_every_n_weeks(dt.date(), rule["every_n_weeks"], rule["anchor_date"]):
        return False
    return True


def is_cron_representable(rule: Optional[Dict[str, Any]]) -> bool:
    """
    Cron-representable when every_n_weeks is 1/absent and not exotic:
    exotic = both weekdays and days_of_month constrained (cron AND is surprising).
    """
    if not rule:
        return False
    r = normalize_schedule_rule(rule)
    if r["every_n_weeks"] > 1:
        return False
    if r["weekdays"] is not None and r["days_of_month"] is not None:
        return False
    return True


def rule_to_cron(rule: Optional[Dict[str, Any]]) -> Optional[str]:
    """Build a 5-field cron when representable; else None."""
    if not is_cron_representable(rule):
        return None
    r = normalize_schedule_rule(rule)
    minute = str(r["minute"])
    hour = str(r["hour"])
    if r["days_of_month"] is not None:
        dom = ",".join(str(d) for d in r["days_of_month"])
    else:
        dom = "*"
    if r["months"] is not None:
        mon = ",".join(str(m) for m in r["months"])
    else:
        mon = "*"
    if r["weekdays"] is not None:
        dow = ",".join(str(d) for d in r["weekdays"])
    else:
        dow = "*"
    return f"{minute} {hour} {dom} {mon} {dow}"


def rule_to_human(rule: Optional[Dict[str, Any]]) -> str:
    if not rule:
        return "No structured schedule"
    r = normalize_schedule_rule(rule)
    DAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    parts: List[str] = []
    if r["every_n_weeks"] > 1:
        parts.append(f"Every {r['every_n_weeks']} weeks")
        if r["anchor_date"]:
            parts.append(f"(anchor {r['anchor_date']})")
    if r["weekdays"] is not None:
        parts.append("on " + ", ".join(DAY[d] for d in r["weekdays"]))
    if r["days_of_month"] is not None:
        parts.append("DOM " + ",".join(str(d) for d in r["days_of_month"]))
    if r["months"] is not None:
        parts.append("in " + ", ".join(MON[m - 1] for m in r["months"]))
    parts.append(f"at {r['hour']:02d}:{r['minute']:02d}")
    return " ".join(parts)


def compute_next_structured_run(
    rule: Dict[str, Any],
    base_time: Optional[datetime] = None,
    *,
    inclusive: bool = False,
    search_days: int = 400,
) -> Optional[datetime]:
    """
    Next UTC fire for a structured rule (rule fields are civil UTC clock).
    Starts at next minute unless inclusive and base lands exactly on a slot.
    """
    now = base_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    # Work in UTC civil time (same as existing cron humanizer).
    utc_now = now.astimezone(timezone.utc)
    r = normalize_schedule_rule(rule)

    if inclusive and civil_matches_rule(utc_now.replace(second=0, microsecond=0), r):
        return utc_now.replace(second=0, microsecond=0)

    candidate = (utc_now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    # Day-oriented scan: for each day, check the single hour:minute slot.
    day = candidate.date()
    end = day + timedelta(days=search_days)
    while day <= end:
        if r["months"] is not None and day.month not in r["months"]:
            day += timedelta(days=1)
            continue
        if r["days_of_month"] is not None and day.day not in r["days_of_month"]:
            day += timedelta(days=1)
            continue
        slot = datetime(day.year, day.month, day.day, r["hour"], r["minute"], tzinfo=timezone.utc)
        if slot < candidate:
            day += timedelta(days=1)
            continue
        if r["weekdays"] is not None and cron_weekday(slot) not in r["weekdays"]:
            day += timedelta(days=1)
            continue
        if not matches_every_n_weeks(day, r["every_n_weeks"], r["anchor_date"]):
            day += timedelta(days=1)
            continue
        return slot
    return None


def preview_structured(
    rule: Dict[str, Any],
    base_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    nxt = compute_next_structured_run(rule, base_time=base_time, inclusive=False)
    cron = rule_to_cron(rule)
    return {
        "next_run_at": nxt.isoformat() if nxt else None,
        "cron_expression": cron,
        "cron_representable": cron is not None,
        "human": rule_to_human(rule),
    }
