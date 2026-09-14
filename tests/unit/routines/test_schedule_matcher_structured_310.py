"""CARD-310: structured schedule matcher + biweekly alignment."""

from datetime import datetime, timezone

from src.application.routines.matcher import ScheduleMatcher
from src.domain.routines.models import Routine, ScheduleType
from src.domain.routines.schedule_rule import (
    compute_next_structured_run,
    rule_to_cron,
    set_schedule_rule_on_metadata,
)


def _biweekly_tuesday_rule():
    return {
        "months": None,
        "weekdays": [2],  # Tuesday (cron)
        "days_of_month": None,
        "hour": 18,
        "minute": 0,
        "every_n_weeks": 2,
        "anchor_date": "2026-09-01",  # Tuesday
    }


def test_biweekly_tuesday_next_from_morning_same_day():
    rule = _biweekly_tuesday_rule()
    base = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    nxt = compute_next_structured_run(rule, base_time=base, inclusive=False)
    assert nxt == datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)


def test_biweekly_skips_off_week_tuesday():
    rule = _biweekly_tuesday_rule()
    # After Sep 1 18:00 → next aligned Tuesday is Sep 15 (Sep 8 is off-week)
    base = datetime(2026, 9, 1, 19, 0, tzinfo=timezone.utc)
    nxt = compute_next_structured_run(rule, base_time=base, inclusive=False)
    assert nxt == datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc)


def test_structured_routine_matcher_sets_next_and_respects_pause():
    rule = _biweekly_tuesday_rule()
    meta = set_schedule_rule_on_metadata({}, rule)
    r = Routine(
        id="r-biweekly",
        name="Biweekly Tue",
        agent_id="assistant",
        prompt="ping",
        schedule_type=ScheduleType.STRUCTURED,
        enabled=True,
        metadata=meta,
        cron_expression=None,
    )
    base = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    nxt = ScheduleMatcher.compute_next_run(r, base_time=base)
    assert nxt == datetime(2026, 9, 1, 18, 0, tzinfo=timezone.utc)

    paused = r.model_copy(update={"enabled": False, "next_run_at": nxt})
    assert ScheduleMatcher.is_routine_due(paused, current_time=nxt) is False

    due = r.model_copy(update={"enabled": True, "next_run_at": nxt})
    assert ScheduleMatcher.is_routine_due(due, current_time=nxt) is True


def test_weekly_rule_is_cron_representable():
    rule = {
        "weekdays": [1, 2, 3, 4, 5],
        "hour": 9,
        "minute": 0,
        "every_n_weeks": 1,
    }
    assert rule_to_cron(rule) == "0 9 * * 1,2,3,4,5"


def test_biweekly_not_cron_representable():
    assert rule_to_cron(_biweekly_tuesday_rule()) is None
