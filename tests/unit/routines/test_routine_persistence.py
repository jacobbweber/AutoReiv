"""
Unit tests for Routine & Routine Run Persistence in SQLite [REQ-ROUTINE-002].
"""

from datetime import datetime, timezone

import pytest

from src.domain.routines.models import Routine, RoutineRun, RoutineStatus, ScheduleType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_routine_crud(store):
    now = datetime.now(timezone.utc)
    r = Routine(
        id="r-morning",
        name="Morning Brief",
        description="Daily overview",
        agent_id="general-assistant",
        prompt="Synthesize tasks",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=86400,
        cron_expression="0 8 * * *",
        enabled=True,
        last_run_at=None,
        next_run_at=None,
        last_status=RoutineStatus.IDLE,
        created_at=now,
        updated_at=now,
    )

    # Save
    store.save_routine(r)

    # Get
    fetched = store.get_routine("r-morning")
    assert fetched is not None
    assert fetched.name == "Morning Brief"
    assert fetched.interval_seconds == 86400

    # List
    all_routines = store.list_routines()
    assert len(all_routines) == 1

    # Update
    fetched.enabled = False
    fetched.last_status = RoutineStatus.SUCCESS
    store.save_routine(fetched)

    updated = store.get_routine("r-morning")
    assert updated.enabled is False
    assert updated.last_status == RoutineStatus.SUCCESS

    # Delete
    deleted = store.delete_routine("r-morning")
    assert deleted is True
    assert store.get_routine("r-morning") is None


def test_routine_run_logging(store):
    now = datetime.now(timezone.utc)
    r = Routine(
        id="r-sys",
        name="Daily Sysinfo",
        agent_id="linux-sysadmin",
        prompt="Get sysinfo",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)

    run = RoutineRun(
        id="run-101",
        routine_id="r-sys",
        agent_id="linux-sysadmin",
        status=RoutineStatus.SUCCESS,
        output="System healthy: CPU 10%, RAM 40%",
        duration_ms=45.2,
        created_at=now,
    )
    store.record_routine_run(run)

    runs = store.get_routine_runs(routine_id="r-sys")
    assert len(runs) == 1
    assert runs[0].id == "run-101"
    assert "System healthy" in runs[0].output
    assert runs[0].duration_ms == 45.2
