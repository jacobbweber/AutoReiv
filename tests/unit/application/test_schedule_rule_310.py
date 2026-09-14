"""CARD-310 structured schedule_rule next-fire + biweekly."""
from datetime import datetime, timezone

from src.application.routines.matcher import ScheduleMatcher, schedule_rule_to_cron
from src.domain.routines.models import Routine, RoutineStatus, ScheduleType


def _routine(rule):
    return Routine(
        id="t",
        name="t",
        agent_id="a",
        prompt="p",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 18 * * *",
        enabled=True,
        last_status=RoutineStatus.IDLE,
        metadata={"schedule_rule": rule},
    )


def test_biweekly_tuesday_18_skips_off_week():
    rule = {
        "weekdays": [1],
        "hour": 18,
        "minute": 0,
        "every_n_weeks": 2,
        "anchor_date": "2026-09-07",
        "timezone": "America/New_York",
    }
    base = datetime(2026, 9, 8, 23, 0, tzinfo=timezone.utc)
    nxt = ScheduleMatcher.compute_next_run(_routine(rule), base_time=base)
    assert nxt is not None
    assert nxt.date().isoformat() >= "2026-09-21"


def test_cron_representable_when_weekly():
    rule = {"weekdays": [0, 1, 2, 3, 4], "hour": 9, "minute": 0, "every_n_weeks": 1}
    cron = schedule_rule_to_cron(rule)
    assert cron is not None
    assert cron.startswith("0 9")


def test_cron_none_when_biweekly():
    assert schedule_rule_to_cron({"hour": 6, "minute": 0, "every_n_weeks": 2, "anchor_date": "2026-01-01"}) is None


def test_disabled_not_due():
    r = _routine({"hour": 0, "minute": 0, "every_n_weeks": 1})
    r.enabled = False
    assert ScheduleMatcher.is_routine_due(r, datetime.now(timezone.utc)) is False
