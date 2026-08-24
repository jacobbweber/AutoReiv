"""
Cron Schedule Humanizer & Next-Run Calculator [REQ-ROUT-001].
Provides bidirectional human-readable cron translations and precise next run ETA calculations.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def cron_to_human(cron_expr: str) -> str:
    """
    Translate standard 5-part cron expressions into clean, human-readable English strings.
    """
    expr = cron_expr.strip()
    parts = expr.split()
    if len(parts) != 5:
        return f"Custom schedule: {expr}"

    minute, hour, dom, month, dow = parts

    # 1. Every minute
    if expr == "* * * * *":
        return "Every minute"

    # 2. Every N minutes (*/N * * * *)
    if minute.startswith("*/") and hour == "*" and dom == "*" and month == "*" and dow == "*":
        step = minute[2:]
        return f"Every {step} minutes"

    # 3. Every hour at minute X (X * * * *)
    if minute.isdigit() and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return f"Every hour at minute {minute}"

    # 4. Every N hours at minute X (X */N * * *)
    if minute.isdigit() and hour.startswith("*/") and dom == "*" and month == "*" and dow == "*":
        step = hour[2:]
        return f"Every {step} hours"

    # 5. Daily at HH:MM UTC (M H * * *)
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow == "*":
        return f"Daily at {int(hour):02d}:{int(minute):02d} UTC"

    # 6. Weekly on Day at HH:MM UTC (M H * * D)
    if minute.isdigit() and hour.isdigit() and dom == "*" and month == "*" and dow.isdigit():
        day_idx = int(dow) % 7
        day_name = DAY_NAMES[day_idx]
        return f"Weekly on {day_name} at {int(hour):02d}:{int(minute):02d} UTC"

    # 7. Monthly on Dth at HH:MM UTC (M H D * *)
    if minute.isdigit() and hour.isdigit() and dom.isdigit() and month == "*" and dow == "*":
        day_num = int(dom)
        suffix = "th"
        if day_num in (1, 21, 31):
            suffix = "st"
        elif day_num in (2, 22):
            suffix = "nd"
        elif day_num in (3, 23):
            suffix = "rd"
        return f"Monthly on the {day_num}{suffix} at {int(hour):02d}:{int(minute):02d} UTC"

    return f"Cron ({expr})"


def _matches_cron_field(val: int, field: str) -> bool:
    """Check if an integer value matches a cron field component."""
    if field == "*":
        return True
    if field.startswith("*/"):
        try:
            step = int(field[2:])
            return val % step == 0
        except ValueError:
            return False
    if "," in field:
        parts = field.split(",")
        return any(_matches_cron_field(val, p.strip()) for p in parts)
    try:
        return val == int(field)
    except ValueError:
        return False


def compute_next_run_eta(
    cron_expr: str,
    from_time: Optional[datetime] = None,
) -> Tuple[datetime, str]:
    """
    Compute the exact next UTC execution datetime and a human-friendly ETA string.
    """
    now = from_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    parts = cron_expr.strip().split()
    if len(parts) != 5:
        # Fallback to 1 hour ahead
        next_dt = now + timedelta(hours=1)
        return next_dt, "in 1 hour"

    min_f, hour_f, dom_f, mon_f, dow_f = parts

    # Search forward minute-by-minute (up to 31 days)
    # Start at next minute boundary
    candidate = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    max_minutes = 31 * 24 * 60

    for _ in range(max_minutes):
        # cron DOW: 0=Sun, 1=Mon, ..., 6=Sat, 7=Sun
        # python weekday(): 0=Mon, 6=Sun -> (candidate.weekday() + 1) % 7 gives 0 for Sun
        dow_val = (candidate.weekday() + 1) % 7

        if (
            _matches_cron_field(candidate.minute, min_f)
            and _matches_cron_field(candidate.hour, hour_f)
            and _matches_cron_field(candidate.day, dom_f)
            and _matches_cron_field(candidate.month, mon_f)
            and (_matches_cron_field(dow_val, dow_f) or _matches_cron_field(7 if dow_val == 0 else dow_val, dow_f))
        ):
            delta = candidate - now
            total_seconds = int(delta.total_seconds())

            if total_seconds < 60:
                eta_str = f"in {total_seconds}s"
            elif total_seconds < 3600:
                mins = total_seconds // 60
                eta_str = f"in {mins}m"
            elif total_seconds < 86400:
                hrs = total_seconds // 3600
                rem_mins = (total_seconds % 3600) // 60
                eta_str = f"in {hrs}h {rem_mins}m" if rem_mins > 0 else f"in {hrs}h"
            else:
                days = total_seconds // 86400
                rem_hrs = (total_seconds % 86400) // 3600
                eta_str = f"in {days}d {rem_hrs}h" if rem_hrs > 0 else f"in {days}d"

            return candidate, eta_str

        candidate += timedelta(minutes=1)

    # Fallback if no match within 31 days
    fallback_dt = now + timedelta(hours=1)
    return fallback_dt, "in 1 hour"
