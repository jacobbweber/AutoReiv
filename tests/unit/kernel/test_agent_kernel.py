"""
Unit tests for AgentKernel ReAct Execution Loop & Streaming Events [REQ-KERNEL-003, REQ-KERNEL-006].
"""

import json
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
        name="handoff_to_agent",
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
                            name="handoff_to_agent",
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
        allowed_tool_names=["handoff_to_agent"],
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


@pytest.mark.asyncio
async def test_stream_turn_emits_nested_handoff_approval(store, collector, registry):
    def parked_handoff(target_agent_id, task_directive):
        return {
            "status": "approval_required",
            "approval_id": "appr_child_1",
            "tool_name": "cli_exec",
            "arguments": {"command": "ipconfig"},
            "message": "Parked for operator approval (appr_child_1).",
            "recipient_agent_id": "autoreiv",
        }

    registry.register_tool(
        name="handoff_to_agent",
        description="Delegate subtask",
        parameters={
            "type": "object",
            "properties": {
                "target_agent_id": {"type": "string"},
                "task_directive": {"type": "string"},
            },
        },
        handler=parked_handoff,
    )

    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[
                        ToolCall(
                            id="call_handoff_park",
                            name="handoff_to_agent",
                            arguments={
                                "target_agent_id": "autoreiv",
                                "task_directive": "List system info using cli_exec",
                            },
                        )
                    ],
                    is_finished=True,
                    finish_reason="tool_calls",
                ),
            ],
            [
                StreamChunk(
                    content="Waiting on operator approval.",
                    is_finished=True,
                    finish_reason="stop",
                ),
            ],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Coordinator",
        system_prompt="You are helpful.",
        allowed_tool_names=["handoff_to_agent"],
    )
    session = store.create_session(agent_id=profile.id, title="Nested HITL")
    events = []
    async for evt in kernel.stream_turn(
        agent=profile,
        session_id=session.id,
        user_content="Ask AutoReiv for system info",
    ):
        events.append(evt)

    park_events = [e for e in events if e.event_type == KernelEventType.APPROVAL_REQUIRED]
    assert park_events, [e.event_type for e in events]
    ev = park_events[0]
    assert ev.approval_id == "appr_child_1"
    assert ev.tool_call["name"] == "cli_exec"
    assert ev.tool_call["arguments"]["command"] == "ipconfig"

    complete_ev = next(e for e in events if e.event_type == KernelEventType.HANDOFF_COMPLETE)
    assert complete_ev.handoff["status"] == "approval_required"
    leftover = "Waiting on operator approval."
    token_text = "".join(e.content or "" for e in events if e.event_type == KernelEventType.TOKEN)
    assert leftover not in token_text
    assert llm.stream_chunks, "second scripted stream turn must remain unused after park"
    types = [e.event_type for e in events]
    assert KernelEventType.TURN_END in types
    assert types.index(KernelEventType.APPROVAL_REQUIRED) < types.index(KernelEventType.TURN_END)
    after_park_tokens = [
        e for e in events[events.index(park_events[0]) + 1 :] if e.event_type == KernelEventType.TOKEN
    ]
    assert after_park_tokens == []


@pytest.mark.asyncio
async def test_run_turn_stops_on_parked_tool(store, collector, registry):
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
            ),
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=collector,
        hitl_engine=HITLApprovalEngine(store=store),
    )
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="sre",
        system_prompt="x",
        allowed_tool_names=["cli_exec"],
    )
    session = store.create_session(agent_id=profile.id, title="Park run_turn")
    msg = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="Run dir",
    )
    parked = json.loads(msg.content)
    assert parked["status"] == "approval_required"
    assert parked["tool_name"] == "cli_exec"
    assert parked["arguments"]["command"] == "dir"
    assert parked["approval_id"]



@pytest.mark.asyncio
async def test_stream_turn_stops_after_park_no_second_llm_turn(store, collector, registry):
    leftover = "Would you like to approve this command? Just say the word."
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[ToolCall(id="c_park", name="cli_exec", arguments={"command": "dir"})],
                    is_finished=True,
                    finish_reason="tool_calls",
                ),
            ],
            [
                StreamChunk(content=leftover, is_finished=True, finish_reason="stop"),
            ],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=collector,
        hitl_engine=HITLApprovalEngine(store=store),
    )
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="sre",
        system_prompt="x",
        allowed_tool_names=["cli_exec"],
    )
    session = store.create_session(agent_id=profile.id, title="Park stream_turn")
    events = []
    async for evt in kernel.stream_turn(
        agent=profile,
        session_id=session.id,
        user_content="Run dir",
    ):
        events.append(evt)

    types = [e.event_type for e in events]
    assert KernelEventType.APPROVAL_REQUIRED in types
    assert KernelEventType.TURN_END in types
    assert types.index(KernelEventType.APPROVAL_REQUIRED) < types.index(KernelEventType.TURN_END)
    token_text = "".join(e.content or "" for e in events if e.event_type == KernelEventType.TOKEN)
    assert leftover not in token_text
    assert llm.stream_chunks, "second scripted stream turn must remain unused after park"
    assert leftover in (llm.stream_chunks[0][0].content or "")


def _seed_parked_history(store, session_id, agent_id, tool_result):
    store.save_message(
        session_id=session_id,
        agent_id=agent_id,
        message=ChatMessage(role=Role.USER, content="Run dir"),
    )
    store.save_message(
        session_id=session_id,
        agent_id=agent_id,
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[ToolCall(id="c_park", name="cli_exec", arguments={"command": "dir"})],
        ),
    )
    store.save_message(
        session_id=session_id,
        agent_id=agent_id,
        message=ChatMessage(
            role=Role.TOOL,
            content=tool_result,
            tool_call_id="c_park",
            name="cli_exec",
        ),
    )


@pytest.mark.asyncio
async def test_stream_turn_resume_without_new_user_message(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [StreamChunk(content="Directory listing looks fine.", is_finished=True, finish_reason="stop")],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="sre",
        system_prompt="x",
        allowed_tool_names=["cli_exec"],
    )
    session = store.create_session(agent_id=profile.id, title="Resume after approve")
    _seed_parked_history(store, session.id, profile.id, "Output of dir: OK")

    events = []
    async for evt in kernel.stream_turn(
        agent=profile,
        session_id=session.id,
        user_content="should not be saved",
        resume=True,
    ):
        events.append(evt)

    types = [e.event_type for e in events]
    assert KernelEventType.TOKEN in types
    token_text = "".join(e.content or "" for e in events if e.event_type == KernelEventType.TOKEN)
    assert "Directory listing looks fine." in token_text
    assert KernelEventType.TURN_END in types

    messages = store.get_messages(session.id)
    user_msgs = [m for m in messages if m.role == Role.USER]
    assert len(user_msgs) == 1
    assert user_msgs[0].content == "Run dir"
    assert all(m.content != "should not be saved" for m in user_msgs)


@pytest.mark.asyncio
async def test_stream_turn_resume_after_reject_emits_token(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [StreamChunk(content="Understood, I will try another approach.", is_finished=True, finish_reason="stop")],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="sre",
        system_prompt="x",
        allowed_tool_names=["cli_exec"],
    )
    session = store.create_session(agent_id=profile.id, title="Resume after reject")
    _seed_parked_history(store, session.id, profile.id, "Rejected. Tool did not run.")

    events = []
    async for evt in kernel.stream_turn(agent=profile, session_id=session.id, resume=True):
        events.append(evt)

    token_text = "".join(e.content or "" for e in events if e.event_type == KernelEventType.TOKEN)
    assert "Understood, I will try another approach." in token_text
    user_msgs = [m for m in store.get_messages(session.id) if m.role == Role.USER]
    assert len(user_msgs) == 1
    assert user_msgs[0].content == "Run dir"




@pytest.mark.asyncio
async def test_run_turn_resume_without_new_user_message(store, collector, registry):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="Directory listing looks fine."),
                finish_reason="stop",
            ),
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="sre",
        system_prompt="x",
        allowed_tool_names=["cli_exec"],
    )
    session = store.create_session(agent_id=profile.id, title="Resume run_turn")
    _seed_parked_history(store, session.id, profile.id, "Output of dir: OK")

    msg = await kernel.run_turn(
        agent=profile,
        session_id=session.id,
        user_content="should not be saved",
        resume=True,
    )
    assert "Directory listing looks fine." in (msg.content or "")
    user_msgs = [m for m in store.get_messages(session.id) if m.role == Role.USER]
    assert len(user_msgs) == 1
    assert user_msgs[0].content == "Run dir"
    assert all(m.content != "should not be saved" for m in user_msgs)


@pytest.mark.asyncio
async def test_stream_turn_resume_replays_nested_park(store, collector, registry):
    leftover = "I should not talk after a nested park replay."
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[
            [StreamChunk(content=leftover, is_finished=True, finish_reason="stop")],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Coordinator",
        system_prompt="You are helpful.",
        allowed_tool_names=["handoff_to_agent"],
    )
    session = store.create_session(agent_id=profile.id, title="Replay nested park")
    store.save_message(session_id=session.id, agent_id=profile.id, message=ChatMessage(role=Role.USER, content="Ask AutoReiv"))
    store.save_message(
        session_id=session.id,
        agent_id=profile.id,
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[ToolCall(id="h1", name="handoff_to_agent", arguments={"target_agent_id": "autoreiv"})],
        ),
    )
    store.save_message(
        session_id=session.id,
        agent_id=profile.id,
        message=ChatMessage(
            role=Role.TOOL,
            content=json.dumps(
                {
                    "status": "approval_required",
                    "approval_id": "appr_child_2",
                    "tool_name": "cli_exec",
                    "arguments": {"command": "dir"},
                    "message": "Parked for operator approval (appr_child_2).",
                    "recipient_agent_id": "autoreiv",
                }
            ),
            name="handoff_to_agent",
            tool_call_id="h1",
        ),
    )
    events = []
    async for evt in kernel.stream_turn(agent=profile, session_id=session.id, resume=True):
        events.append(evt)
    types = [e.event_type for e in events]
    assert KernelEventType.APPROVAL_REQUIRED in types
    assert KernelEventType.HANDOFF_COMPLETE in types
    assert KernelEventType.TURN_END in types
    park = next(e for e in events if e.event_type == KernelEventType.APPROVAL_REQUIRED)
    assert park.approval_id == "appr_child_2"
    assert park.tool_call["name"] == "cli_exec"
    complete = next(e for e in events if e.event_type == KernelEventType.HANDOFF_COMPLETE)
    assert complete.handoff["status"] == "approval_required"
    token_text = "".join(e.content or "" for e in events if e.event_type == KernelEventType.TOKEN)
    assert leftover not in token_text
    assert llm.stream_chunks, "resume must not start a new LLM turn when replaying a nested park"
    users = [m for m in store.get_messages(session.id) if m.role == Role.USER]
    assert len(users) == 1


@pytest.mark.asyncio
async def test_stream_turn_aclose_before_nested_complete(store, collector, registry):
    """Parent LLM stream must be aclosed before a nested complete() [REQ-ORCH-023]."""

    class HoldingStreamLLM(LLMProviderPort):
        provider_id = "mock"

        def __init__(self):
            self.stream_open = False
            self.complete_while_stream_open = False
            self.complete_calls = 0
            self._streamed_tools = False

        async def complete(self, request: CompletionRequest) -> CompletionResponse:
            self.complete_calls += 1
            if self.stream_open:
                self.complete_while_stream_open = True
            return CompletionResponse(
                model=request.model,
                message=ChatMessage(role=Role.ASSISTANT, content="nested-ok"),
                finish_reason="stop",
            )

        async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
            if self._streamed_tools:
                yield StreamChunk(content="done", is_finished=True, finish_reason="stop")
                return
            self._streamed_tools = True
            self.stream_open = True
            try:
                yield StreamChunk(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="probe_1",
                            name="nested_complete_probe",
                            arguments={},
                        )
                    ],
                    is_finished=True,
                    finish_reason="tool_calls",
                )
            finally:
                self.stream_open = False

    llm = HoldingStreamLLM()

    async def probe_handler():
        await llm.complete(
            CompletionRequest(
                model="mock/model",
                messages=[ChatMessage(role=Role.USER, content="child")],
            )
        )
        return "probe-ok"

    registry.register_tool(
        name="nested_complete_probe",
        description="Simulate nested complete during parent stream",
        parameters={"type": "object", "properties": {}},
        handler=probe_handler,
    )

    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(
        gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector
    )
    profile = AgentProfile(
        id="conductor",
        name="Conductor",
        description="Conductor",
        system_prompt="You orchestrate.",
        allowed_tool_names=["nested_complete_probe"],
    )
    session = store.create_session(agent_id=profile.id, title="aclose before tools")
    events = []
    async for evt in kernel.stream_turn(
        agent=profile, session_id=session.id, user_content="delegate"
    ):
        events.append(evt)

    assert llm.complete_calls == 1
    assert llm.complete_while_stream_open is False
    assert llm.stream_open is False
    assert KernelEventType.TOOL_END in [e.event_type for e in events]


@pytest.mark.asyncio
async def test_run_turn_caps_nested_context_window(store, collector, registry):
    """Handoff complete() must not inherit Chat 131k [REQ-ORCH-028]."""
    llm = MockScriptedLLM(
        [
            CompletionResponse(
                model="qwen3.8:latest",
                message=ChatMessage(role=Role.ASSISTANT, content="pong"),
                finish_reason="stop",
            )
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    kernel._resolve_context_limit = lambda model: 131072
    profile = AgentProfile(
        id="coding",
        name="Coding",
        description="coder",
        system_prompt="You write code.",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["task_tracker"],
    )
    session = store.create_session(agent_id=profile.id, title="Nested ctx cap")
    await kernel.run_turn(agent=profile, session_id=session.id, user_content="pong")
    assert llm.requests, "complete() was not called"
    req = llm.requests[0]
    assert req.num_ctx == 32768
    assert req.max_tokens == 8192


@pytest.mark.asyncio
async def test_stream_turn_uses_full_context_window(store, collector, registry):
    """Chat/child stream_turn keeps the model window. 32k cap is run_turn only [REQ-ORCH-037]."""
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[[StreamChunk(content="pong", is_finished=True, finish_reason="stop")]],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    kernel._resolve_context_limit = lambda model: 131072
    profile = AgentProfile(
        id="coding",
        name="Coding",
        description="coder",
        system_prompt="You write code.",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["task_tracker"],
    )
    session = store.create_session(agent_id=profile.id, title="Full ctx stream")
    events = []
    async for ev in kernel.stream_turn(agent=profile, session_id=session.id, user_content="pong"):
        events.append(ev)
    assert llm.requests, "stream() was not called"
    req = llm.requests[0]
    assert req.num_ctx == 131072
    assert req.num_ctx != 32768

