"""
Unit tests for Routine Executor & Autonomous Turn Execution [REQ-ROUTINE-004, REQ-ROUTINE-005].
"""

from typing import AsyncIterator

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.routines.executor import RoutineExecutor
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

    def __init__(self, response_text: str = "Routine executed successfully."):
        self.response_text = response_text

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content=self.response_text),
            finish_reason="stop",
            usage={"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(content=self.response_text, is_finished=True, finish_reason="stop")


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def collector(store):
    return TelemetryCollector(store=store)


@pytest.fixture
def executor(store, collector):
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=collector)
    mock_llm = MockScriptedLLM("Here is your morning briefing: all systems nominal.")
    gateway = MultiProviderGateway()
    gateway.register_provider(mock_llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=tool_reg, state_store=store, telemetry=collector)

    return RoutineExecutor(
        agent_registry=agent_reg,
        kernel=kernel,
        state_store=store,
        telemetry=collector,
    )


@pytest.mark.asyncio
async def test_execute_routine_success(store, executor):
    r = Routine(
        id="r-morning-test",
        name="Morning Test",
        agent_id="general-assistant",
        prompt="Synthesize tasks",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)

    run = await executor.execute_routine(r)

    assert run.status == RoutineStatus.SUCCESS
    assert "morning briefing" in run.output
    assert run.duration_ms > 0

    # Verify routine state updated in DB
    updated_routine = store.get_routine("r-morning-test")
    assert updated_routine.last_status == RoutineStatus.SUCCESS
    assert updated_routine.last_run_at is not None

    # Verify run logged in DB
    runs = store.get_routine_runs("r-morning-test")
    assert len(runs) == 1
    assert runs[0].status == RoutineStatus.SUCCESS


@pytest.mark.asyncio
async def test_trigger_routine_by_id(store, executor):
    r = Routine(
        id="r-trigger-test",
        name="Trigger Test",
        agent_id="system-agent",
        prompt="Check health",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)

    run = await executor.trigger_routine_by_id("r-trigger-test")
    assert run is not None
    assert run.status == RoutineStatus.SUCCESS
    assert run.routine_id == "r-trigger-test"


@pytest.mark.asyncio
async def test_execute_routine_missing_agent_fails_gracefully(store, executor):
    r = Routine(
        id="r-bad-agent",
        name="Bad Agent Routine",
        agent_id="nonexistent-agent",
        prompt="Do something",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
    )
    store.save_routine(r)

    run = await executor.execute_routine(r)
    assert run.status == RoutineStatus.FAILED
    assert "not found" in run.error_message.lower()
