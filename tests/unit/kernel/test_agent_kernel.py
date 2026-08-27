"""
Unit tests for AgentKernel ReAct Execution Loop & Streaming Events [REQ-KERNEL-003, REQ-KERNEL-006].
"""

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
)
from src.domain.kernel.models import (
    AgentProfile,
    AgentTone,
    KernelEventType,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class MockScriptedLLM(LLMProviderPort):
    """Mock LLM returning scripted sequence of responses."""

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
        parameters={"type": "object", "properties": {"cmd": {"type": "string"}}},
        handler=lambda cmd: f"Output of {cmd}: OK",
    )
    return reg


@pytest.mark.asyncio
async def test_agent_kernel_single_turn(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="Hello Jacob, how can I assist you?"),
                finish_reason="stop",
                usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            )
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)

    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Daily assistant",
        system_prompt="You are helpful.",
        tone=AgentTone.FRIENDLY,
        allowed_tool_names=["task_tracker"],
    )

    session = store.create_session(agent_id=profile.id, title="Test Single Turn")
    response_msg = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="Hello AutoReiv!",
    )

    assert response_msg.role == Role.ASSISTANT
    assert response_msg.content == "Hello Jacob, how can I assist you?"

    # Verify message persistence
    messages = store.get_messages(session.id)
    assert len(messages) == 2
    assert messages[0].role == Role.USER
    assert messages[0].content == "Hello AutoReiv!"
    assert messages[1].role == Role.ASSISTANT

    # Verify telemetry recorded
    kpis = collector.get_global_kpis()
    assert kpis["total_turns"] == 1
    assert kpis["total_tokens"] == 18


@pytest.mark.asyncio
async def test_agent_kernel_multi_turn_react_tool_execution(store, collector, registry):
    # Turn 1: Model asks for tool call
    # Turn 2: Model returns final answer after seeing tool output
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="call_99", name="task_tracker", arguments={"action": "list"})],
                ),
                finish_reason="tool_calls",
            ),
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="Your tasks are: Task action 'list' executed successfully.",
                ),
                finish_reason="stop",
            ),
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)

    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=["task_tracker"],
    )

    session = store.create_session(agent_id=profile.id, title="Test Tool Execution")
    final_msg = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="List my tasks",
    )

    assert "Your tasks are:" in final_msg.content

    # Verify full message trace: [User, Assistant(ToolCall), ToolResponse, Assistant(Final)]
    messages = store.get_messages(session.id)
    assert len(messages) == 4
    assert messages[0].role == Role.USER
    assert messages[1].tool_calls is not None
    assert messages[2].role == Role.TOOL
    assert messages[2].tool_call_id == "call_99"
    assert messages[3].role == Role.ASSISTANT


@pytest.mark.asyncio
async def test_agent_kernel_unauthorized_tool_call_denial(store, collector, registry):
    # Agent tries to execute cli_exec, but is only authorized for task_tracker
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="call_unauth", name="cli_exec", arguments={"cmd": "rm -rf /"})],
                ),
                finish_reason="tool_calls",
            ),
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="I do not have permission to run CLI commands.",
                ),
                finish_reason="stop",
            ),
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)

    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=["task_tracker"],  # NOT cli_exec
    )

    session = store.create_session(agent_id=profile.id, title="Test Unauth Tool")
    final_msg = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="Delete everything",
    )

    assert "permission" in final_msg.content

    messages = store.get_messages(session.id)
    assert len(messages) == 4
    # The tool result message in history should reflect the permission denial
    assert "not authorized" in messages[2].content.lower()


@pytest.mark.asyncio
async def test_agent_kernel_cycle_detection(store, collector, registry):
    # Model gets stuck calling identical tool with identical args
    identical_call = ToolCall(id="call_cycle", name="task_tracker", arguments={"action": "loop"})
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[identical_call]),
                finish_reason="tool_calls",
            ),
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[identical_call]),
                finish_reason="tool_calls",
            ),
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[identical_call]),
                finish_reason="tool_calls",
            ),
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)

    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=["task_tracker"],
        max_turns=5,
    )

    session = store.create_session(agent_id=profile.id, title="Test Cycle Detection")
    final_msg = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="Get stuck",
    )

    assert "cycle" in final_msg.content.lower() or "terminated" in final_msg.content.lower()


@pytest.mark.asyncio
async def test_agent_kernel_streaming_events(store, collector, registry):
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
                StreamChunk(content="Final ", reasoning_content=""),
                StreamChunk(content="streaming output.", is_finished=True, finish_reason="stop"),
            ],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)

    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=["task_tracker"],
    )

    session = store.create_session(agent_id=profile.id, title="Test Stream Events")
    events = []
    async for evt in kernel.stream_turn(agent=profile, session_id=session.id, user_content="Stream my task"):
        events.append(evt)

    event_types = [e.event_type for e in events]
    assert KernelEventType.TOKEN in event_types
    assert KernelEventType.TOOL_START in event_types
    assert KernelEventType.TOOL_END in event_types
    assert KernelEventType.TURN_END in event_types


@pytest.mark.asyncio
async def test_agent_kernel_streaming_handoff_events(store, collector, registry):
    registry.register_tool(
        name="delegate_task",
        description="Delegate subtask",
        parameters={
            "type": "object",
            "properties": {"target_agent": {"type": "string"}, "task_intent": {"type": "string"}},
        },
        handler=lambda target_agent, task_intent: f"Delegation to {target_agent} for '{task_intent}' completed",
    )

    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[
                        ToolCall(
                            id="call_handoff_1",
                            name="delegate_task",
                            arguments={"target_agent": "linux-sysadmin", "task_intent": "Inspect disk usage"},
                        )
                    ],
                    is_finished=True,
                    finish_reason="tool_calls",
                ),
            ],
            [
                StreamChunk(
                    content="The Linux Sysadmin confirmed disk health.", is_finished=True, finish_reason="stop"
                ),
            ],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)

    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=["delegate_task"],
    )

    session = store.create_session(agent_id=profile.id, title="Test Handoff Stream Events")
    events = []
    async for evt in kernel.stream_turn(agent=profile, session_id=session.id, user_content="Check my disk"):
        events.append(evt)

    event_types = [e.event_type for e in events]
    assert KernelEventType.HANDOFF_START in event_types
    assert KernelEventType.HANDOFF_COMPLETE in event_types

    start_ev = next(e for e in events if e.event_type == KernelEventType.HANDOFF_START)
    assert start_ev.handoff["recipient"] == "linux-sysadmin"
    assert start_ev.handoff["directive"] == "Inspect disk usage"

    complete_ev = next(e for e in events if e.event_type == KernelEventType.HANDOFF_COMPLETE)
    assert complete_ev.handoff["recipient"] == "linux-sysadmin"
    assert complete_ev.handoff["status"] == "completed"
