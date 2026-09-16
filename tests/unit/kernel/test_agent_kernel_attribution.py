"""Unit tests for CARD-337: AgentKernel Granular Telemetry Recording [REQ-TEL-002, REQ-TEL-003]."""

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class MockScriptedLLM(LLMProviderPort):
    provider_id: str = "mock"

    def __init__(self, responses: List[CompletionResponse] = None, stream_chunks: List[List[StreamChunk]] = None):
        self.responses = list(responses or [])
        self.stream_chunks = list(stream_chunks or [])
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if not self.responses:
            return CompletionResponse(
                model=request.model,
                message=ChatMessage(role=Role.ASSISTANT, content="Default mock response"),
                finish_reason="stop",
            )
        return self.responses.pop(0)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        if not self.stream_chunks:
            yield StreamChunk(content="Default ", is_finished=False)
            yield StreamChunk(content="stream response", is_finished=True, finish_reason="stop")
            return
        for c in self.stream_chunks.pop(0):
            yield c


@pytest.fixture
def kernel_fixture(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    tool_reg = ScopedToolRegistry()

    def dummy_tool(x: int = 1) -> str:
        return f"result: {x}"

    tool_reg.register_tool(
        name="dummy_tool",
        description="A dummy tool for testing token schema sizing",
        parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
        handler=dummy_tool,
    )

    gateway = MultiProviderGateway()
    llm = MockScriptedLLM()
    gateway.register_provider(llm)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
        hitl_engine=HITLApprovalEngine(store=store),
        data_dir=str(tmp_path),
    )
    return kernel, store, llm


@pytest.mark.asyncio
async def test_run_turn_records_granular_telemetry_breakdown(kernel_fixture):
    """[REQ-TEL-002, REQ-TEL-003] run_turn logs token_breakdown and timing_breakdown in metadata."""
    kernel, store, _ = kernel_fixture
    store.create_session(agent_id="assistant", session_id="sess_attr_1")

    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="A helpful assistant",
        system_prompt="You are a helpful assistant with tools.",
        allowed_tool_names=["dummy_tool"],
    )

    await kernel.run_turn(
        agent=profile,
        session_id="sess_attr_1",
        user_content="Hello, please test telemetry attribution!",
    )

    spans = store.get_telemetry_spans(session_id="sess_attr_1")
    turn_spans = [s for s in spans if s.span_type == "turn"]
    assert len(turn_spans) >= 1
    latest_span = turn_spans[-1]

    meta = latest_span.metadata or {}
    assert "token_breakdown" in meta, f"Missing token_breakdown in metadata: {meta}"
    assert "timing_breakdown" in meta, f"Missing timing_breakdown in metadata: {meta}"

    tb = meta["token_breakdown"]
    assert tb["user_prompt"] > 0
    assert tb["agent_persona"] > 0
    assert tb["tool_schemas"] > 0
    assert tb["completion"] > 0
    assert tb["scaffold_tokens"] > 0
    assert tb["scaffold_ratio"] > 0

    tm = meta["timing_breakdown"]
    assert tm["total_round_trip_ms"] >= 0
    assert "harness_prep_ms" in tm


@pytest.mark.asyncio
async def test_stream_turn_records_granular_telemetry_breakdown(kernel_fixture):
    """[REQ-TEL-002, REQ-TEL-003] stream_turn logs token_breakdown and timing_breakdown in metadata."""
    kernel, store, _ = kernel_fixture
    store.create_session(agent_id="direct", session_id="sess_attr_2")

    # Direct agent with zero tools
    direct_profile = AgentProfile(
        id="direct",
        name="Direct",
        description="A direct assistant",
        system_prompt="You are a direct, concise assistant.",
        tools=[],
    )

    async for _ in kernel.stream_turn(
        agent=direct_profile,
        session_id="sess_attr_2",
        user_content="Direct question without any tools.",
    ):
        pass

    spans = store.get_telemetry_spans(session_id="sess_attr_2")
    turn_spans = [s for s in spans if s.span_type == "turn"]
    assert len(turn_spans) >= 1
    span = turn_spans[-1]

    meta = span.metadata or {}
    assert "token_breakdown" in meta
    assert "timing_breakdown" in meta

    tb = meta["token_breakdown"]
    assert tb["tool_schemas"] == 0, "Direct agent must have 0 tool schema tokens"
    assert tb["progressive_skills"] == 0
    assert tb["user_prompt"] > 0
    assert tb["completion"] > 0

    tm = meta["timing_breakdown"]
    assert tm["ttft_ms"] is not None
    assert tm["tokens_per_second"] is not None
