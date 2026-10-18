"""CARD-712: Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop and decompose agent_kernel.py."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import AsyncIterator, List
from unittest.mock import MagicMock

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
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.domain.orchestration.models import ReactState
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard

KERNEL_DIR = Path(__file__).resolve().parents[3] / "src" / "application" / "kernel"


class _ScriptedLLM(LLMProviderPort):
    provider_id: str = "mock"

    def __init__(
        self,
        responses: List[CompletionResponse] | None = None,
        stream_chunks: List[List[StreamChunk]] | None = None,
    ):
        self.responses = list(responses or [])
        self.stream_chunks = list(stream_chunks or [])
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if not self.responses:
            return CompletionResponse(
                model=request.model,
                message=ChatMessage(role=Role.ASSISTANT, content="Unexpected extra LLM turn"),
                finish_reason="stop",
            )
        return self.responses.pop(0)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        if not self.stream_chunks:
            yield StreamChunk(content="Unexpected extra stream turn", is_finished=True, finish_reason="stop")
            return
        for chunk in self.stream_chunks.pop(0):
            yield chunk


def _make_kernel():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    collector = TelemetryCollector(store=store)
    registry = ScopedToolRegistry()
    return store, collector, registry


@pytest.mark.asyncio
async def test_run_turn_parks_on_nested_handoff_approval_without_second_llm_call():
    """run_turn must stop and park on nested child HITL approval output just like stream_turn [CARD-712]."""
    store, collector, registry = _make_kernel()

    def parked_handoff(target_agent_id: str, task_directive: str):
        return {
            "status": "approval_required",
            "approval_id": "appr_nested_712",
            "tool_name": "cli_exec",
            "arguments": {"command": "uname -a"},
            "message": "Parked for operator approval (appr_nested_712).",
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

    llm = _ScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="call_nested_park",
                            name="handoff_to_agent",
                            arguments={"target_agent_id": "autoreiv", "task_directive": "Run uname"},
                        )
                    ],
                ),
                finish_reason="tool_calls",
            ),
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="Should never run after nested park"),
                finish_reason="stop",
            ),
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Coordinator",
        system_prompt="You coordinate.",
        allowed_skill=["tool:handoff_to_agent"],
    )
    session = store.create_session(agent_id=profile.id, title="Nested Park in run_turn")

    msg = await kernel.run_turn(agent=profile, session_id=session.id, user_content="Delegate uname")
    parked = json.loads(msg.content)
    assert parked["status"] == "approval_required"
    assert parked["approval_id"] == "appr_nested_712"
    assert parked["tool_name"] == "cli_exec"
    assert kernel.react_state == ReactState.PARKED
    assert len(llm.requests) == 1, "run_turn must stop immediately after nested park without a second LLM call"


@pytest.mark.asyncio
async def test_stream_turn_forwards_routine_id_to_tool_policy_gate():
    """stream_turn must accept routine_id and forward it to _gate_tool_call just like run_turn [CARD-712]."""
    store, collector, registry = _make_kernel()
    registry.register_tool(
        name="cli_exec",
        description="Run command",
        parameters={"type": "object", "properties": {"command": {"type": "string"}}},
        handler=lambda command: f"ran {command}",
    )
    llm = _ScriptedLLM(
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[ToolCall(id="c_rt", name="cli_exec", arguments={"command": "echo routine"})],
                    is_finished=True,
                    finish_reason="tool_calls",
                )
            ]
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
        description="SRE",
        system_prompt="You run checks.",
        allowed_skill=["tool:cli_exec"],
    )
    session = store.create_session(agent_id=profile.id, title="Routine Stream Gate")

    events = [
        ev
        async for ev in kernel.stream_turn(
            agent=profile,
            session_id=session.id,
            user_content="Run routine check",
            routine_id="routine_712",
        )
    ]
    assert any(e.event_type == KernelEventType.APPROVAL_REQUIRED for e in events)
    pending = store.get_pending_approvals(session_id=session.id)
    assert len(pending) == 1
    assert pending[0].get("routine_id") == "routine_712"


@pytest.mark.asyncio
async def test_run_turn_and_stream_turn_format_tool_errors_identically():
    """Failed tool rows in both run_turn and stream_turn start with 'Tool Error: ' [CARD-712]."""
    store, collector, registry = _make_kernel()

    def failing_tool():
        raise RuntimeError("boom_712")

    registry.register_tool(
        name="task_tracker",
        description="Failing tool",
        parameters={"type": "object", "properties": {}},
        handler=failing_tool,
    )
    llm = _ScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[ToolCall(id="c_err_sync", name="task_tracker", arguments={})],
                ),
                finish_reason="tool_calls",
            ),
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="The tool failed."),
                finish_reason="stop",
            ),
        ],
        stream_chunks=[
            [
                StreamChunk(
                    tool_calls=[ToolCall(id="c_err_stream", name="task_tracker", arguments={})],
                    is_finished=True,
                    finish_reason="tool_calls",
                )
            ],
            [StreamChunk(content="The tool failed.", is_finished=True, finish_reason="stop")],
        ],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Assistant",
        system_prompt="You help.",
        allowed_skill=["tool:task_tracker"],
    )

    s_sync = store.create_session(agent_id=profile.id, title="Sync Error")
    await kernel.run_turn(agent=profile, session_id=s_sync.id, user_content="Try tool")
    sync_tool_msgs = [m for m in store.get_messages(s_sync.id) if m.role == Role.TOOL]

    s_stream = store.create_session(agent_id=profile.id, title="Stream Error")
    async for _ in kernel.stream_turn(agent=profile, session_id=s_stream.id, user_content="Try tool"):
        pass
    stream_tool_msgs = [m for m in store.get_messages(s_stream.id) if m.role == Role.TOOL]

    assert len(sync_tool_msgs) == 1
    assert len(stream_tool_msgs) == 1
    assert sync_tool_msgs[0].content.startswith("Tool Error: ")
    assert sync_tool_msgs[0].content == stream_tool_msgs[0].content


def test_kernel_modules_under_800_lines_and_no_direct_adapter_imports():
    """All kernel modules must be under 800 lines and must not import gateway adapters directly [CARD-712]."""
    for expected in ("agent_kernel.py", "react_loop.py", "system_prompt_builder.py", "model_resolver.py"):
        mod_path = KERNEL_DIR / expected
        assert mod_path.is_file(), f"Missing extracted kernel module: {expected}"

    forbidden_adapters = {
        "src.infrastructure.gateway.ollama_adapter",
        "src.infrastructure.gateway.anthropic_adapter",
        "src.infrastructure.gateway.openai_adapter",
    }
    for py_file in sorted(KERNEL_DIR.glob("*.py")):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) < 800, f"{py_file.name} has {len(lines)} lines (ceiling is 800)"
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in forbidden_adapters:
                raise AssertionError(f"{py_file.name} directly imports {node.module} instead of GatewayProviderFactory")


def test_agent_kernel_delegates_provider_creation_to_factory():
    """_ensure_agent_provider_adapter uses GatewayProviderFactory.create_adapter [CARD-712]."""
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    gateway = MultiProviderGateway()
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=ScopedToolRegistry(),
        state_store=store,
        telemetry=MagicMock(),
    )
    profile = AgentProfile(
        id="custom-agent",
        name="Custom",
        description="Custom",
        system_prompt="You help.",
        provider="openai",
        api_base_url="http://127.0.0.1:9999/v1",
        api_key="sk-test-712",
    )
    kernel._ensure_agent_provider_adapter(profile)
    assert "openai" in gateway._providers
    assert gateway._providers["openai"].base_url == "http://127.0.0.1:9999/v1"
