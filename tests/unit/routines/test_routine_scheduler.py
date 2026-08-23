"""
Unit tests for RoutineScheduler & Background Engine [REQ-ROUTINE-003, REQ-ROUTINE-004].
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.routines.executor import RoutineExecutor
from src.application.routines.scheduler import RoutineScheduler
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.domain.routines.models import Routine, RoutineStatus, ScheduleType
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class MockScriptedLLM(LLMProviderPort):
    provider_id: str = "mock"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content="Autonomous scheduler run output"),
            finish_reason="stop",
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(content="Autonomous scheduler run output", is_finished=True, finish_reason="stop")


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def scheduler(store):
    collector = TelemetryCollector(store=store)
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=collector)
    mock_llm = MockScriptedLLM()
    gateway = MultiProviderGateway()
    gateway.register_provider(mock_llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=tool_reg, state_store=store, telemetry=collector)

    executor = RoutineExecutor(
        agent_registry=agent_reg,
        kernel=kernel,
        state_store=store,
        telemetry=collector,
    )

    return RoutineScheduler(
        executor=executor,
        state_store=store,
        tick_interval_seconds=0.05,
    )


@pytest.mark.asyncio
async def test_scheduler_bootstrap_defaults(store, scheduler):
    # Seed default Day-1 routines
    RoutineScheduler.seed_default_routines(store)

    routines = store.list_routines()
    assert len(routines) == 4
    ids = [r.id for r in routines]
    assert "morning-briefing" in ids
    assert "daily-sysinfo" in ids
    assert "nightly-hygiene" in ids
    assert "hourly-sre-pulse" in ids


@pytest.mark.asyncio
async def test_scheduler_tick_executes_due_routines(store, scheduler):
    now = datetime.now(timezone.utc)

    # 1. Due routine (last_run was 2 hours ago with 1hr interval)
    r_due = Routine(
        id="r-due-1",
        name="Due Routine",
        agent_id="general-assistant",
        prompt="Synthesize",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        enabled=True,
        last_run_at=now - timedelta(hours=2),
    )
    # 2. Not due routine (last_run was 10 mins ago with 1hr interval)
    r_not_due = Routine(
        id="r-not-due",
        name="Not Due",
        agent_id="general-assistant",
        prompt="Wait",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        enabled=True,
        last_run_at=now - timedelta(minutes=10),
    )
    store.save_routine(r_due)
    store.save_routine(r_not_due)

    executed_runs = await scheduler.tick()

    assert len(executed_runs) == 1
    assert executed_runs[0].routine_id == "r-due-1"
    assert executed_runs[0].status == RoutineStatus.SUCCESS


@pytest.mark.asyncio
async def test_scheduler_background_start_and_stop(store, scheduler):
    r = Routine(
        id="r-fast",
        name="Fast Routine",
        agent_id="system-agent",
        prompt="Quick pulse",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=1,
        enabled=True,
        last_run_at=None,
    )
    store.save_routine(r)

    # Start background task
    task = asyncio.create_task(scheduler.start())
    await asyncio.sleep(0.15)
    await scheduler.stop()
    await task

    assert scheduler.is_running is False
    runs = store.get_routine_runs("r-fast")
    assert len(runs) >= 1
