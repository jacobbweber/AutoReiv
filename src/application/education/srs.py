"""Fixed 1-3-7-30 spaced repetition schedule [CARD-242 / REQ-EDU-RR-003]."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

SRS_INTERVALS_DAYS: tuple[int, ...] = (1, 3, 7, 30)


def next_due_after_grade(
    *,
    correct: bool,
    interval_stage: int,
    now: datetime | None = None,
) -> Tuple[int, datetime]:
    """Return (new_stage, next_due) after a binary grade.

    Miss resets to stage 0 (1 day). Pass advances one rung on 1-3-7-30 (capped).
    """
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stage = max(0, int(interval_stage or 0))
    if not correct:
        new_stage = 0
    else:
        new_stage = min(stage + 1, len(SRS_INTERVALS_DAYS) - 1)
    days = SRS_INTERVALS_DAYS[new_stage]
    return new_stage, base + timedelta(days=days)
