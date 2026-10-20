"""
Unit tests for AgentKernel streaming resume, context windows, and active project prompt injection [REQ-KERNEL-006].
"""

import json
from typing import AsyncIterator

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
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
from tests.unit.kernel.test_agent_kernel import (
    MockScriptedLLM,
    collector,
    registry,
    store,
)

__all__ = ["collector", "registry", "store"]


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
        allowed_skill=["tool:handoff_to_agent"],
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
        allowed_skill=["tool:nested_complete_probe"],
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
async def test_run_turn_uses_the_agents_own_context_window(store, collector, registry):
    """CARD-576: nested run_turn sends the agent's context window (no 32k cap, so Ollama does not reload)."""
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
    kernel._resolve_context_limit = lambda *args, **kwargs: 131072
    profile = AgentProfile(
        id="coding",
        name="Coding",
        description="coder",
        system_prompt="You write code.",
        tone=AgentTone.TECHNICAL,
        allowed_skill=["tool:task_tracker"],
    )
    session = store.create_session(agent_id=profile.id, title="Nested ctx")
    await kernel.run_turn(agent=profile, session_id=session.id, user_content="pong")
    assert llm.requests, "complete() was not called"
    req = llm.requests[0]
    assert req.num_ctx == 131072
    assert req.max_tokens == 32768  # CARD-586: the reply limit (default 32768, under a quarter of 131072)


@pytest.mark.asyncio
async def test_stream_turn_uses_full_context_window(store, collector, registry):
    """Chat/child stream_turn keeps the model window [REQ-ORCH-037]."""
    llm = MockScriptedLLM(
        responses=[],
        stream_chunks=[[StreamChunk(content="pong", is_finished=True, finish_reason="stop")]],
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)
    kernel._resolve_context_limit = lambda *args, **kwargs: 131072
    profile = AgentProfile(
        id="coding",
        name="Coding",
        description="coder",
        system_prompt="You write code.",
        tone=AgentTone.TECHNICAL,
        allowed_skill=["tool:task_tracker"],
    )
    session = store.create_session(agent_id=profile.id, title="Full ctx stream")
    events = []
    async for ev in kernel.stream_turn(agent=profile, session_id=session.id, user_content="pong"):
        events.append(ev)
    assert llm.requests, "stream() was not called"
    req = llm.requests[0]
    assert req.num_ctx == 131072
    assert req.num_ctx != 32768


def test_agent_kernel_injects_active_selected_project(store, collector, registry, tmp_path, monkeypatch):
    """Verify that the active selected project from ProjectsService is injected into system prompt."""
    from src.application.sdlc.projects_service import ProjectsService

    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(tmp_path))  # CARD-728: projects live in one folder
    (tmp_path / "agentic-test").mkdir()
    proj_svc = ProjectsService(store=store)
    proj_svc.set_selected(slug="agentic-test", path=str(tmp_path / "agentic-test"))

    gateway = MultiProviderGateway()
    kernel = AgentKernel(gateway=gateway, tool_registry=registry, state_store=store, telemetry=collector)

    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Active-project software engineer",
        system_prompt="You plan, build, and test.",
        tone=AgentTone.TECHNICAL,
        allowed_skill=["software-development"],
    )

    msg = kernel._build_effective_system_message(agent=profile, user_content="hello")
    assert "## Active Selected Project" in msg.content
    assert "agentic-test" in msg.content
    assert str(tmp_path / "agentic-test") in msg.content
