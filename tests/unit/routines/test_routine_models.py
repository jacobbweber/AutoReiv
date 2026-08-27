"""
Unit tests for Routine Domain Models & Day-1 Manifests [REQ-ROUTINE-001, REQ-ROUTINE-006].
"""

from datetime import datetime, timezone

from src.domain.routines.manifests import (
    BUILTIN_ROUTINES,
    get_builtin_routine,
)
from src.domain.routines.models import (
    Routine,
    RoutineRun,
    RoutineStatus,
    ScheduleType,
)


def test_routine_model_instantiation():
    now = datetime.now(timezone.utc)
    r = Routine(
        id="test-routine",
        name="Test Routine",
        description="A test routine",
        agent_id="general-assistant",
        prompt="Perform a test run",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=600,
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    assert r.id == "test-routine"
    assert r.agent_id == "general-assistant"
    assert r.interval_seconds == 600
    assert r.enabled is True
    assert r.last_status == RoutineStatus.IDLE


def test_routine_run_model():
    now = datetime.now(timezone.utc)
    run = RoutineRun(
        id="run-1",
        routine_id="test-routine",
        agent_id="general-assistant",
        status=RoutineStatus.SUCCESS,
        output="Task completed successfully.",
        duration_ms=125.5,
        created_at=now,
    )
    assert run.id == "run-1"
    assert run.status == RoutineStatus.SUCCESS
    assert run.duration_ms == 125.5


def test_builtin_day1_routines_manifests():
    assert len(BUILTIN_ROUTINES) == 4
    ids = [r.id for r in BUILTIN_ROUTINES]
    assert "morning-briefing" in ids
    assert "daily-sysinfo" in ids
    assert "nightly-hygiene" in ids
    assert "hourly-sre-pulse" in ids

    # Check Morning Briefing
    mb = get_builtin_routine("morning-briefing")
    assert mb is not None
    assert mb.agent_id == "assistant"
    assert "task tracker" in mb.prompt.lower() or "tasks" in mb.prompt.lower()

    # Check Daily Sysinfo
    ds = get_builtin_routine("daily-sysinfo")
    assert ds is not None
    assert ds.agent_id == "autoreiv"
    assert "system" in ds.prompt.lower()

    # Check Nightly Hygiene
    nh = get_builtin_routine("nightly-hygiene")
    assert nh is not None
    assert nh.agent_id == "assistant"

    # Check Hourly SRE Pulse
    sp = get_builtin_routine("hourly-sre-pulse")
    assert sp is not None
    assert sp.agent_id == "autoreiv"
    assert sp.interval_seconds == 3600
