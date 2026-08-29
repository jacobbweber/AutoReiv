"""
Named ReAct overlay on AgentKernel [REQ-KERNEL-001, REQ-KERNEL-002].
"""

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
)
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.domain.orchestration.models import ReactState
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class MockScriptedLLM(LLMProviderPort):
    provider_id: str = "mock"

    def __init__(self, responses: List[CompletionResponse], stream_chunks: List[List[StreamChunk]] = None):
        self.responses = list(responses)
        self.stream_chunks = list(stream_chunks or [])
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if not self.responses:
            return CompletionResponse(
                model=request.model,
                message=ChatMessage(role=Role.ASSISTANT, content="Default mock reply"),
                finish_reason="stop",
            )
        return self.responses.pop(0)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        if not self.stream_chunks:
            yield StreamChunk(content="Mock stream reply", is_finished=True, finish_reason="stop")
            return
        chunks = self.stream_chunks.pop(0)
        for c in chunks:
            yield c


class BoomLLM(LLMProviderPort):
    provider_id: str = "mock"

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        raise ConnectionError("Failed to connect to provider")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        raise ConnectionError("Failed to connect to provider")
        yield StreamChunk(content="", is_finished=True)


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def collector(store):
    return TelemetryCollector(store=store)


@pytest.fixture
def registry():
    reg = ScopedToolRegistry()
    reg.register_tool(
        name="task_tracker",
        description="Track tasks",
        parameters={"type": "object", "properties": {"action": {"type": "string"}}},
        handler=lambda action: f"Task action '{action}' executed successfully",
    )
    reg.register_tool(
        name="cli_exec",
        description="Run CLI",
        parameters={"type": "object", "properties": {"command": {"type": "string"}}},
        handler=lambda command=None, cmd=None: f"Output of {command or cmd}: OK",
    )
    return reg


def _profile(**kwargs) -> AgentProfile:
    defaults = dict(
        id="general-assistant",
        name="General Assistant",
        description="Daily assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=["task_tracker", "cli_exec"],
    )
    defaults.update(kwargs)
    return AgentProfile(**defaults)


def _kernel(store, collector, registry, llm, hitl=False) -> AgentKernel:
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    return AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=collector,
        hitl_engine=HITLApprovalEngine(store=store) if hitl else None,
    )


def _react_states(events):
    return [e.react["react_state"] for e in events if e.event_type == KernelEventType.REACT_STATE]


@pytest.mark.asyncio
async def test_run_turn_success_sets_done(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="Hello"),
                finish_reason="stop",
            )
        ]
    )
    kernel = _kernel(store, collector, registry, llm)
    session = store.create_session(agent_id="general-assistant", title="done")
    msg = await kernel.run_turn(agent=_profile(), session_id=session.id, user_content="hi")
    assert msg.content == "Hello"
    assert kernel.react_state == ReactState.DONE


@pytest.mark.asyncio
async def test_run_turn_park_sets_parked(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="c1", name="cli_exec", arguments={"command": "dir"})],
                ),
                finish_reason="tool_calls",
            )
        ]
    )
    kernel = _kernel(store, collector, registry, llm, hitl=True)
    session = store.create_session(agent_id="general-assistant", title="park")
    msg = await kernel.run_turn(agent=_profile(), session_id=session.id, user_content="Run dir")
    assert "approval_required" in (msg.content or "")
    assert kernel.react_state == ReactState.PARKED


@pytest.mark.asyncio
async def test_run_turn_budget_exhaust_sets_failed(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="c1", name="task_tracker", arguments={"action": "ping"})],
                ),
                finish_reason="tool_calls",
            )
        ]
    )
    kernel = _kernel(store, collector, registry, llm)
    session = store.create_session(agent_id="general-assistant", title="budget")
    msg = await kernel.run_turn(
        agent=_profile(max_turns=1),
        session_id=session.id,
        user_content="ping",
    )
    assert "Max turn budget" in (msg.content or "")
    assert kernel.react_state == ReactState.FAILED


@pytest.mark.asyncio
async def test_run_turn_provider_failure_sets_failed(store, collector, registry):
    kernel = _kernel(store, collector, registry, BoomLLM())
    session = store.create_session(agent_id="general-assistant", title="boom")
    with pytest.raises(Exception, match="Failed to connect"):
        await kernel.run_turn(agent=_profile(), session_id=session.id, user_content="hi")
    assert kernel.react_state == ReactState.FAILED


@pytest.mark.asyncio
async def test_stream_turn_success_yields_thinking_then_done(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[[StreamChunk(content="Final answer.", is_finished=True, finish_reason="stop")]],
    )
    kernel = _kernel(store, collector, registry, llm)
    session = store.create_session(agent_id="general-assistant", title="stream-done")
    events = []
    async for evt in kernel.stream_turn(agent=_profile(), session_id=session.id, user_content="hi"):
        events.append(evt)
    assert _react_states(events) == ["THINKING", "DONE"]
    assert kernel.react_state == ReactState.DONE
    assert events[0].event_type == KernelEventType.REACT_STATE
    assert events[0].react["turn_idx"] == 0
    assert events[0].react["assigned_agent_id"] == "general-assistant"


@pytest.mark.asyncio
async def test_stream_turn_park_yields_parked(store, collector, registry):
    leftover = "Would you like to approve this command?"
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[ToolCall(id="c_park", name="cli_exec", arguments={"command": "dir"})],
                    is_finished=True,
                    finish_reason="tool_calls",
                )
            ],
            [StreamChunk(content=leftover, is_finished=True, finish_reason="stop")],
        ],
    )
    kernel = _kernel(store, collector, registry, llm, hitl=True)
    session = store.create_session(agent_id="general-assistant", title="stream-park")
    events = []
    async for evt in kernel.stream_turn(agent=_profile(), session_id=session.id, user_content="Run dir"):
        events.append(evt)
    states = _react_states(events)
    assert states == ["THINKING", "CALLING_TOOLS", "PARKED"]
    assert kernel.react_state == ReactState.PARKED
    assert KernelEventType.APPROVAL_REQUIRED in [e.event_type for e in events]
    assert leftover not in "".join(e.content or "" for e in events if e.event_type == KernelEventType.TOKEN)
    assert llm.stream_chunks, "second scripted stream turn must remain unused after park"


@pytest.mark.asyncio
async def test_stream_turn_budget_exhaust_yields_failed(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[ToolCall(id="c1", name="task_tracker", arguments={"action": "ping"})],
                    is_finished=True,
                    finish_reason="tool_calls",
                )
            ]
        ],
    )
    kernel = _kernel(store, collector, registry, llm)
    session = store.create_session(agent_id="general-assistant", title="stream-budget")
    events = []
    async for evt in kernel.stream_turn(
        agent=_profile(max_turns=1),
        session_id=session.id,
        user_content="ping",
    ):
        events.append(evt)
    assert _react_states(events) == ["THINKING", "CALLING_TOOLS", "FAILED"]
    assert kernel.react_state == ReactState.FAILED


@pytest.mark.asyncio
async def test_stream_turn_tools_then_done_yields_named_states(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(content="Thinking...", reasoning_content=""),
                StreamChunk(
                    tool_calls=[ToolCall(id="call_st", name="task_tracker", arguments={"action": "sync"})],
                    is_finished=True,
                    finish_reason="tool_calls",
                ),
            ],
            [
                StreamChunk(content="Final streaming output.", is_finished=True, finish_reason="stop"),
            ],
        ],
    )
    kernel = _kernel(store, collector, registry, llm)
    session = store.create_session(agent_id="general-assistant", title="stream-tools")
    events = []
    async for evt in kernel.stream_turn(agent=_profile(), session_id=session.id, user_content="sync"):
        events.append(evt)
    assert _react_states(events) == ["THINKING", "CALLING_TOOLS", "THINKING", "DONE"]
    assert kernel.react_state == ReactState.DONE


@pytest.mark.asyncio
async def test_stream_turn_provider_failure_yields_failed(store, collector, registry):
    kernel = _kernel(store, collector, registry, BoomLLM())
    session = store.create_session(agent_id="general-assistant", title="stream-boom")
    events = []
    async for evt in kernel.stream_turn(agent=_profile(), session_id=session.id, user_content="hi"):
        events.append(evt)
    assert _react_states(events) == ["THINKING", "FAILED"]
    assert kernel.react_state == ReactState.FAILED
    assert any(e.event_type == KernelEventType.ERROR for e in events)
    assert "Delegation Completed" not in " ".join(e.content or "" for e in events)


@pytest.mark.asyncio
async def test_run_turn_persists_react_state_on_phase(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="Hello"),
                finish_reason="stop",
            )
        ]
    )
    kernel = _kernel(store, collector, registry, llm)
    session = store.create_session(agent_id="general-assistant", title="persist")
    orch = JobPhaseOrchestrator(store)
    job = orch.create_single_phase_job(goal="hi", session_id=session.id, agent_id="general-assistant")
    phase_id = job.current_phase_id
    await kernel.run_turn(
        agent=_profile(),
        session_id=session.id,
        user_content="hi",
        phase_id=phase_id,
        job_id=job.id,
    )
    phase = store.get_phase(phase_id)
    assert phase.react_state == ReactState.DONE


@pytest.mark.asyncio
async def test_stream_turn_persists_parked_on_phase(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[ToolCall(id="c_park", name="cli_exec", arguments={"command": "dir"})],
                    is_finished=True,
                    finish_reason="tool_calls",
                )
            ]
        ],
    )
    kernel = _kernel(store, collector, registry, llm, hitl=True)
    session = store.create_session(agent_id="general-assistant", title="persist-park")
    orch = JobPhaseOrchestrator(store)
    job = orch.create_single_phase_job(goal="park", session_id=session.id, agent_id="general-assistant")
    events = []
    async for evt in kernel.stream_turn(
        agent=_profile(),
        session_id=session.id,
        user_content="Run dir",
        phase_id=job.current_phase_id,
        job_id=job.id,
    ):
        events.append(evt)
    phase = store.get_phase(job.current_phase_id)
    assert phase.react_state == ReactState.PARKED
    payload = next(e.react for e in events if e.event_type == KernelEventType.REACT_STATE and e.react["react_state"] == "PARKED")
    assert payload["job_id"] == job.id
    assert payload["phase_id"] == job.current_phase_id
    assert payload["assigned_agent_id"] == "general-assistant"
