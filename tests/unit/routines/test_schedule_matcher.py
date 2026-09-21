"""
Unit tests for ScheduleMatcher [REQ-ROUTINE-003].
"""

from datetime import datetime, timedelta, timezone

from src.application.routines.matcher import ScheduleMatcher
from src.domain.routines.models import Routine, ScheduleType


def test_disabled_routine_is_not_due():
    r = Routine(
        id="r-disabled",
        name="Disabled",
        agent_id="general-assistant",
        prompt="Test",
        enabled=False,
    )
    assert ScheduleMatcher.is_routine_due(r) is False


def test_first_time_routine_is_due():
    r = Routine(
        id="r-first",
        name="First Time",
        agent_id="general-assistant",
        prompt="Test",
        enabled=True,
        last_run_at=None,
    )
    assert ScheduleMatcher.is_routine_due(r) is True


def test_interval_schedule_evaluation():
    now = datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)

    # Run 30 minutes ago with 1 hour interval -> Not due
    r1 = Routine(
        id="r-int1",
        name="Interval 1hr",
        agent_id="general-assistant",
        prompt="Test",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        last_run_at=now - timedelta(minutes=30),
    )
    assert ScheduleMatcher.is_routine_due(r1, current_time=now) is False

    # Run 65 minutes ago with 1 hour interval -> Due
    r2 = Routine(
        id="r-int2",
        name="Interval 1hr Due",
        agent_id="general-assistant",
        prompt="Test",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        last_run_at=now - timedelta(minutes=65),
    )
    assert ScheduleMatcher.is_routine_due(r2, current_time=now) is True


def test_compute_next_run_interval():
    now = datetime(2026, 8, 23, 12, 0, 0, tzinfo=timezone.utc)
    r = Routine(
        id="r-next",
        name="Next Interval",
        agent_id="general-assistant",
        prompt="Test",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=1800,
    )
    next_time = ScheduleMatcher.compute_next_run(r, base_time=now)
    assert next_time == now + timedelta(seconds=1800)

def test_timezone_aware_next_run_not_utc_cron():
    """CARD-111: 21:00 ET weekdays, not 21:00 UTC, not 02:00 local."""
    from src.domain.routines.manifests import SKILL_EVAL_SLEEP_ROUTINE

    routine = SKILL_EVAL_SLEEP_ROUTINE.model_copy(update={"enabled": True})
    base = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
    nxt = ScheduleMatcher.compute_next_run(routine, base_time=base)
    assert nxt == datetime(2026, 9, 1, 1, 0, 0, tzinfo=timezone.utc)
    paused = SKILL_EVAL_SLEEP_ROUTINE
    assert paused.enabled is False
    assert ScheduleMatcher.is_routine_due(paused, current_time=nxt) is False


def test_cron_cold_boot_not_due():
    """CARD-406: CRON routines on fresh boot (last_run_at=None, next_run_at=None) must not fire eagerly."""
    r = Routine(
        id="weekly-note-rollover",
        name="Weekly Note Rollover",
        agent_id="autoreiv",
        prompt="Perform rollover",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 0 * * 1",
        enabled=True,
        last_run_at=None,
        next_run_at=None,
    )
    # Even if next_run_at is None, a cron routine must not fire on cold boot
    now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
    assert ScheduleMatcher.is_routine_due(r, current_time=now) is False


def test_compute_next_run_cron():
    """CARD-406: compute_next_run on CRON routine calculates correct future UTC timestamp."""
    # 2026-09-21 is Monday 12:00 UTC. Next Monday 00:00 UTC is 2026-09-28 00:00 UTC.
    base = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)
    r = Routine(
        id="weekly-note-rollover",
        name="Weekly Note Rollover",
        agent_id="autoreiv",
        prompt="Perform rollover",
        schedule_type=ScheduleType.CRON,
        cron_expression="0 0 * * 1",
        enabled=True,
    )
    nxt = ScheduleMatcher.compute_next_run(r, base_time=base)
    assert nxt == datetime(2026, 9, 28, 0, 0, 0, tzinfo=timezone.utc)

