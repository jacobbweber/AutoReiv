"""CARD-098: child stream_turn keeps full context; generation semaphore queues [REQ-ORCH-037, REQ-ORCH-038]."""

import asyncio
from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.generation_semaphore import (
    DEFAULT_MAX_CONCURRENT_GENERATIONS,
    HandoffBatchExceedsCapError,
    clamp_max_concurrent_generations,
    validate_handoff_batch,
)
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class RecordingLLM(LLMProviderPort):
    provider_id = "mock"

    def __init__(self):
        self.requests: List[CompletionRequest] = []
        self.complete_calls = 0
        self.in_flight = 0
        self.max_in_flight = 0

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.complete_calls += 1
        self.requests.append(request)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0.05)
        self.in_flight -= 1
        return CompletionResponse(
            model=request.model,
            message=ChatMessage(role=Role.ASSISTANT, content="nested-complete"),
            finish_reason="stop",
        )

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0.05)
            yield StreamChunk(content="child-ok", is_finished=True, finish_reason="stop")
        finally:
            self.in_flight -= 1


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=tmp_path / "card098.db")
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_child_stream_turn_does_not_apply_32k_run_turn_cap(store):
    """Child handoff uses stream_turn full context, not NESTED_COMPLETE_MAX_CTX [REQ-ORCH-037]."""
    llm = RecordingLLM()
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    registry_tools = ScopedToolRegistry()
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry_tools,
        state_store=store,
        telemetry=TelemetryCollector(store=store),
    )
    kernel._resolve_context_limit = lambda *args, **kwargs: 131072
    profile = AgentProfile(
        id="specialist-agent",
        name="Specialist",
        description="coder",
        system_prompt="You write code.",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=[],
        max_turns=5,
    )
    agents = BuiltinAgentRegistry(profiles=[profile], state_store=store)
    engine = HandoffIsolationEngine(agent_registry=agents, state_store=store, kernel=kernel)
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_full_ctx",
        task_intent="Implement the card",
        packet=HandoffPacket(
            goal="Implement the card",
            facts=["isolated"],
            constraints=["no push"],
            done_when="done",
            budget={"max_turns": 10},
        ),
        depth=1,
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "completed"
    assert llm.complete_calls == 0
    assert llm.requests, "child stream_turn did not hit the provider"
    assert llm.requests[0].num_ctx == 131072
    assert llm.requests[0].num_ctx != 32768


@pytest.mark.asyncio
async def test_gateway_semaphore_queues_overlapping_complete():
    """Two concurrent complete() calls do not overlap when max=1. Extra work queues [REQ-ORCH-038]."""
    llm = RecordingLLM()
    gateway = MultiProviderGateway(max_concurrent_generations=1)
    gateway.register_provider(llm)
    req = CompletionRequest(
        model="mock/x",
        messages=[ChatMessage(role=Role.USER, content="hi")],
    )
    await asyncio.gather(gateway.complete(req), gateway.complete(req))
    assert llm.max_in_flight == 1
    assert llm.complete_calls == 2


@pytest.mark.asyncio
async def test_gateway_semaphore_queues_overlapping_stream():
    llm = RecordingLLM()
    gateway = MultiProviderGateway(max_concurrent_generations=1)
    gateway.register_provider(llm)
    req = CompletionRequest(
        model="mock/x",
        messages=[ChatMessage(role=Role.USER, content="hi")],
        stream=True,
    )

    async def drain():
        chunks = []
        agen = gateway.stream(req, demux_reasoning=False)
        try:
            async for chunk in agen:
                chunks.append(chunk)
        finally:
            closer = getattr(agen, "aclose", None)
            if callable(closer):
                await closer()
        return chunks

    await asyncio.gather(drain(), drain())
    assert llm.max_in_flight == 1


def test_generation_semaphore_default_is_one():
    assert DEFAULT_MAX_CONCURRENT_GENERATIONS == 1
    assert clamp_max_concurrent_generations(1) == 1
    assert clamp_max_concurrent_generations(3) == 3
    with pytest.raises(ValueError):
        clamp_max_concurrent_generations(0)
    with pytest.raises(ValueError):
        clamp_max_concurrent_generations(4)


def test_handoff_batch_over_cap_errors_no_truncate():
    with pytest.raises(HandoffBatchExceedsCapError) as exc:
        validate_handoff_batch(2, max_concurrent=1)
    msg = str(exc.value).lower()
    assert "exceeds" in msg
    assert "not truncated" in msg
    validate_handoff_batch(1, max_concurrent=1)
