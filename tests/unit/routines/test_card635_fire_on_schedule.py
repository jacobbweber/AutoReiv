"""CARD-635: routines fire only at their scheduled time; missed runs are skipped, never caught up."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.routines.executor import RoutineExecutor
from src.application.routines.matcher import MISSED_RUN_GRACE, ScheduleMatcher
from src.application.routines.scheduler import RoutineScheduler
from src.domain.routines.models import Routine, RoutineStatus, ScheduleType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _routine(**kw) -> Routine:
    base = dict(
        id="r635",
        name="R635",
        agent_id="autoreiv",
        prompt="pulse",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        enabled=True,
    )
    base.update(kw)
    return Routine(**base)


class _Agent:
    id = "autoreiv"


class _Registry:
    def __init__(self, known=True):
        self.known = known

    def get_profile(self, agent_id):
        return _Agent() if self.known else None


class _BoomKernel:
    calls = 0

    async def run_turn(self, **kw):
        _BoomKernel.calls += 1
        raise RuntimeError("[vllm] Failed to connect")


class _OkKernel:
    calls = 0

    async def run_turn(self, **kw):
        _OkKernel.calls += 1

        class _M:
            content = "ok"

        return _M()


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def _scheduler(store, kernel, known=True):
    ex = RoutineExecutor(agent_registry=_Registry(known), kernel=kernel, state_store=store, telemetry=None)
    return RoutineScheduler(executor=ex, state_store=store, tick_interval_seconds=0.02)


def test_grace_is_about_thirty_minutes():
    assert MISSED_RUN_GRACE == timedelta(minutes=30)


def test_due_within_grace():
    now = datetime.now(timezone.utc)
    r = _routine(next_run_at=now - timedelta(minutes=5))
    assert ScheduleMatcher.is_routine_due(r, current_time=now) is True


def test_missed_beyond_grace_is_not_due():
    now = datetime.now(timezone.utc)
    r = _routine(next_run_at=now - timedelta(hours=2), last_run_at=now - timedelta(hours=3))
    assert ScheduleMatcher.is_routine_due(r, current_time=now) is False


def test_never_ran_is_not_due_without_next_run():
    r = _routine(next_run_at=None, last_run_at=None)
    assert ScheduleMatcher.is_routine_due(r) is False


def test_legacy_row_without_next_run_is_not_due_even_when_interval_elapsed():
    now = datetime.now(timezone.utc)
    r = _routine(next_run_at=None, last_run_at=now - timedelta(hours=5))
    assert ScheduleMatcher.is_routine_due(r, current_time=now) is False


@pytest.mark.asyncio
async def test_tick_skips_missed_run_reschedules_and_logs(store, caplog):
    now = datetime.now(timezone.utc)
    store.save_routine(_routine(next_run_at=now - timedelta(hours=3)))
    _OkKernel.calls = 0
    sched = _scheduler(store, _OkKernel())
    with caplog.at_level(logging.INFO):
        runs = await sched.tick()
    assert runs == []
    assert _OkKernel.calls == 0
    assert store.get_routine_runs("r635") == []
    saved = store.get_routine("r635")
    assert saved.next_run_at > now
    assert "skipped missed run" in caplog.text
    assert "r635" in caplog.text


@pytest.mark.asyncio
async def test_tick_fills_missing_next_run_without_running(store):
    now = datetime.now(timezone.utc)
    store.save_routine(_routine(next_run_at=None, last_run_at=None))
    _OkKernel.calls = 0
    runs = await _scheduler(store, _OkKernel()).tick()
    assert runs == []
    assert _OkKernel.calls == 0
    assert store.get_routine("r635").next_run_at > now


@pytest.mark.asyncio
async def test_start_skips_missed_runs_before_first_tick(store, caplog):
    now = datetime.now(timezone.utc)
    store.save_routine(_routine(next_run_at=now - timedelta(days=1)))
    _OkKernel.calls = 0
    sched = _scheduler(store, _OkKernel())
    with caplog.at_level(logging.INFO):
        task = asyncio.create_task(sched.start())
        await asyncio.sleep(0.1)
        await sched.stop()
        await task
    assert _OkKernel.calls == 0
    assert store.get_routine_runs("r635") == []
    assert "at start" in caplog.text


def test_skip_missed_runs_returns_skipped_ids(store):
    now = datetime.now(timezone.utc)
    store.save_routine(_routine(id="old", next_run_at=now - timedelta(hours=2)))
    store.save_routine(_routine(id="soon", next_run_at=now + timedelta(minutes=10)))
    store.save_routine(_routine(id="off", enabled=False, next_run_at=now - timedelta(hours=2)))
    skipped = _scheduler(store, _OkKernel()).skip_missed_runs(now=now)
    assert skipped == ["old"]
    assert store.get_routine("soon").next_run_at == now + timedelta(minutes=10)


@pytest.mark.asyncio
async def test_failure_moves_next_run_forward(store):
    now = datetime.now(timezone.utc)
    r = _routine(next_run_at=now - timedelta(minutes=1))
    store.save_routine(r)
    run = await _scheduler(store, _BoomKernel()).executor.execute_routine(r)
    assert run.status == RoutineStatus.FAILED
    assert store.get_routine("r635").next_run_at > now


@pytest.mark.asyncio
async def test_missing_agent_moves_next_run_forward(store):
    now = datetime.now(timezone.utc)
    r = _routine(next_run_at=now - timedelta(minutes=1))
    store.save_routine(r)
    run = await _scheduler(store, _OkKernel(), known=False).executor.execute_routine(r)
    assert run.status == RoutineStatus.FAILED
    assert store.get_routine("r635").next_run_at > now


@pytest.mark.asyncio
async def test_failing_routine_does_not_refire_every_tick(store):
    now = datetime.now(timezone.utc)
    store.save_routine(_routine(next_run_at=now - timedelta(minutes=1)))
    _BoomKernel.calls = 0
    sched = _scheduler(store, _BoomKernel())
    for _ in range(4):
        await sched.tick()
    assert _BoomKernel.calls == 1
    assert len(store.get_routine_runs("r635")) == 1


def _app_with(routine: Routine):
    from src.web.app import create_app

    s = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=s)
    s.save_routine(routine)
    return app, s


@pytest.mark.asyncio
async def test_toggle_enable_recomputes_stale_next_run():
    stale = datetime(2026, 10, 2, 1, 0, tzinfo=timezone.utc)
    app, s = _app_with(_routine(id="paused635", enabled=False, next_run_at=stale))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/routines/paused635/toggle")
    assert res.json()["enabled"] is True
    assert s.get_routine("paused635").next_run_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_put_enable_recomputes_stale_next_run():
    stale = datetime(2026, 10, 2, 1, 0, tzinfo=timezone.utc)
    app, s = _app_with(_routine(id="paused635b", enabled=False, next_run_at=stale))
    payload = {"name": "R", "agent_id": "autoreiv", "schedule_type": "interval", "interval_seconds": 3600,
               "prompt_template": "pulse", "enabled": True}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put("/api/routines/paused635b", json=payload)
    assert res.status_code == 200
    assert s.get_routine("paused635b").next_run_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_toggle_pause_keeps_next_run():
    nxt = datetime.now(timezone.utc) + timedelta(hours=3)
    app, s = _app_with(_routine(id="on635", enabled=True, next_run_at=nxt))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/routines/on635/toggle")
    assert res.json()["enabled"] is False
    got = s.get_routine("on635").next_run_at
    assert abs((got - nxt).total_seconds()) < 1
