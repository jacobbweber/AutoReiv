"""
Unit tests for HandoffIsolationEngine kernel delegation and isolation guardrails [REQ-ORCH-003, REQ-A2A-003].
Child path is stream_turn with a packet-only user message [REQ-ORCH-036, REQ-ORCH-037].
"""

import json
from typing import Optional
from unittest.mock import MagicMock

import pytest

from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEvent, KernelEventType
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class StreamTurnKernel:
    """Minimal stream_turn kernel used by handoff tests."""

    def __init__(self, content: str = "ok", error: Optional[Exception] = None, parked: Optional[dict] = None):
        self.content = content
        self.error = error
        self.parked = parked
        self.stream_turn_called = False
        self.run_turn_called = False
        self.passed_agent = None
        self.passed_session_id = None
        self.passed_user_content = None
        self.passed_approval_mode = None
        self.kwargs = None
        self.max_turns = None

    async def run_turn(self, agent, session_id, user_content="", approval_mode="ask"):
        self.run_turn_called = True
        raise AssertionError("child handoff must not call run_turn")

    async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
        self.stream_turn_called = True
        self.passed_agent = agent
        self.passed_session_id = session_id
        self.passed_user_content = user_content
        self.passed_approval_mode = approval_mode
        self.max_turns = getattr(agent, "max_turns", None)
        self.kwargs = {
            "session_id": session_id,
            "approval_mode": approval_mode,
            "user_content": user_content,
            "resume": resume,
        }
        if self.error:
            raise self.error
        if self.parked:
            yield KernelEvent(
                event_type=KernelEventType.APPROVAL_REQUIRED,
                content=self.parked.get("message") or "Approval required",
                approval_id=self.parked.get("approval_id"),
                tool_call={
                    "id": "c1",
                    "name": self.parked.get("tool_name"),
                    "arguments": self.parked.get("arguments") or {},
                },
            )
            yield KernelEvent(
                event_type=KernelEventType.TURN_END,
                content=self.parked.get("message") or "Approval required",
                is_finished=True,
            )
            return
        yield KernelEvent(event_type=KernelEventType.TOKEN, content=self.content)
        yield KernelEvent(event_type=KernelEventType.TURN_END, content=self.content, is_finished=True)


@pytest.fixture
def isolated_engine_setup(tmp_path):
    db_path = tmp_path / "test_handoff.db"
    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    target_profile = AgentProfile(
        id="specialist-agent",
        name="Specialist Agent",
        description="Specialist in diagnostics",
        system_prompt="You are a diagnostics expert.",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["system_info"],
        max_turns=5,
    )

    registry = BuiltinAgentRegistry(
        profiles=[target_profile],
        state_store=store,
    )

    return {
        "store": store,
        "registry": registry,
        "profile": target_profile,
    }


@pytest.mark.asyncio
async def test_handoff_delegates_to_stream_turn(isolated_engine_setup):
    """Verify that HandoffIsolationEngine invokes stream_turn, not run_turn [REQ-ORCH-037]."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    kernel = StreamTurnKernel(content="Diagnostics completed: CPU load 12%, Memory free 74%")
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_001",
        task_intent="Diagnose system load",
        context_payload={"detail": "high"},
        max_turns=3,
        depth=1,
    )

    events = []

    def on_event(event_type, payload):
        events.append((event_type, payload))

    result = await engine.execute_handoff(envelope, on_event=on_event)

    assert result.status == "completed"
    assert "Diagnostics completed" in result.summary
    assert kernel.stream_turn_called is True
    assert kernel.run_turn_called is False
    assert kernel.passed_agent.id == "specialist-agent"
    assert kernel.passed_agent.max_turns == 10
    assert "sess_root_001_child_" in kernel.passed_session_id
    assert "Handoff Packet" in kernel.passed_user_content
    assert "Goal: Diagnose system load" in kernel.passed_user_content
    assert "detail: high" in kernel.passed_user_content
    assert "parent transcript" not in kernel.passed_user_content.lower()

    event_names = [e[0] for e in events]
    assert "handoff_start" in event_names
    assert "handoff_complete" in event_names


@pytest.mark.asyncio
async def test_handoff_requires_stream_turn(isolated_engine_setup):
    """Child path must not fall back to run_turn / execute_turn [REQ-ORCH-037]."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    class LegacyOnlyKernel:
        def __init__(self):
            self.execute_turn_called = False
            self.run_turn_called = False

        async def execute_turn(self, agent, session_id, user_content=""):
            self.execute_turn_called = True
            return MagicMock(content="Legacy kernel response", turns_taken=1)

        async def run_turn(self, agent, session_id, user_content=""):
            self.run_turn_called = True
            return MagicMock(content="run_turn should not run", turns_taken=1)

    kernel = LegacyOnlyKernel()
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_002",
        task_intent="Legacy subtask",
        depth=1,
    )

    result = await engine.execute_handoff(envelope)

    assert result.status == "failed"
    assert "stream_turn" in (result.error_message or "").lower()
    assert kernel.execute_turn_called is False
    assert kernel.run_turn_called is False


@pytest.mark.asyncio
async def test_handoff_handles_kernel_exception_gracefully(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    kernel = StreamTurnKernel(error=RuntimeError("Provider connection reset"))
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_003",
        task_intent="Crash test",
        depth=1,
    )

    result = await engine.execute_handoff(envelope)

    assert result.status == "failed"
    assert "Provider connection reset" in result.error_message


@pytest.mark.asyncio
async def test_handoff_anti_recursion_guardrail(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    kernel = StreamTurnKernel()
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_004",
        task_intent="Deep recursion",
        depth=3,
    )

    result = await engine.execute_handoff(envelope)

    assert result.status == "rejected"
    assert "recursion depth" in result.error_message.lower()
    assert kernel.stream_turn_called is False


@pytest.mark.asyncio
async def test_handoff_self_delegation_guardrail(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=StreamTurnKernel(),
    )

    envelope = HandoffEnvelope(
        sender_agent_id="specialist-agent",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_005",
        task_intent="Self loop",
        depth=1,
    )

    result = await engine.execute_handoff(envelope)

    assert result.status == "rejected"
    assert "self-handoff is forbidden" in result.error_message.lower()


@pytest.mark.asyncio
async def test_handoff_unknown_recipient(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=StreamTurnKernel(),
    )

    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="nonexistent-specialist",
        session_id="sess_root_006",
        task_intent="Ghost subtask",
        depth=1,
    )

    result = await engine.execute_handoff(envelope)

    assert result.status == "failed"
    assert "not found in registry" in result.error_message


@pytest.mark.asyncio
async def test_handoff_maps_child_park_to_approval_required(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    kernel = StreamTurnKernel(
        parked={
            "status": "approval_required",
            "approval_id": "appr_child_1",
            "tool_name": "cli_exec",
            "arguments": {"command": "ipconfig"},
            "message": "Parked for operator approval (appr_child_1).",
        }
    )
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=kernel,
    )
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_park",
        task_intent="Run ipconfig",
        depth=1,
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "approval_required"
    assert result.approval_id == "appr_child_1"
    assert result.parked_tool_name == "cli_exec"
    assert result.parked_arguments["command"] == "ipconfig"
    assert "Parked" in (result.summary or "")


@pytest.mark.asyncio
async def test_handoff_passes_approval_mode_to_stream_turn(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    kernel = StreamTurnKernel(content="ok")
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_root_mode",
        task_intent="Run dir",
        depth=1,
        approval_mode="run",
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "completed"
    assert kernel.kwargs["approval_mode"] == "run"


@pytest.mark.asyncio
async def test_resume_nested_child_continues_without_user_and_unblocks_parent(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    class ResumeKernel:
        def __init__(self):
            self.calls = []

        async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
            self.calls.append(
                {
                    "session_id": session_id,
                    "user_content": user_content,
                    "resume": resume,
                    "approval_mode": approval_mode,
                }
            )
            yield KernelEvent(event_type=KernelEventType.TOKEN, content="ipconfig output ready.")
            yield KernelEvent(
                event_type=KernelEventType.TURN_END,
                content="ipconfig output ready.",
                is_finished=True,
            )

    kernel = ResumeKernel()
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    parent_id = "sess_root_nested"
    child_id = f"{parent_id}_child_abcd1234"
    store.create_session(agent_id="assistant", title="Parent", session_id=parent_id)
    store.create_session(agent_id="specialist-agent", title="Child", session_id=child_id)
    store.save_message(
        session_id=child_id,
        agent_id="specialist-agent",
        message=ChatMessage(role=Role.USER, content="Delegated Subtask Directive:\nRun ipconfig"),
    )
    store.save_message(
        session_id=child_id,
        agent_id="specialist-agent",
        message=ChatMessage(role=Role.TOOL, content="Output: adapters listed", name="cli_exec"),
    )

    result = await engine.resume_nested_child(
        child_session_id=child_id,
        parent_session_id=parent_id,
        agent_id="specialist-agent",
    )
    assert result["status"] == "completed"
    assert kernel.calls and kernel.calls[0]["resume"] is True
    assert kernel.calls[0]["user_content"] is None
    assert kernel.calls[0]["session_id"] == child_id
    child_users = [m for m in store.get_messages(child_id) if m.role == Role.USER]
    assert len(child_users) == 1
    parent_tools = [m for m in store.get_messages(parent_id) if m.role == Role.TOOL]
    assert parent_tools
    assert parent_tools[-1].name == "handoff_to_agent"
    assert "ipconfig output ready." in parent_tools[-1].content


@pytest.mark.asyncio
async def test_resume_nested_child_rebubbles_second_park(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    class ParkAgainKernel:
        async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
            yield KernelEvent(
                event_type=KernelEventType.APPROVAL_REQUIRED,
                content="Parked for operator approval (appr_child_2).",
                approval_id="appr_child_2",
                tool_call={"id": "c2", "name": "cli_exec", "arguments": {"command": "dir"}},
            )
            yield KernelEvent(
                event_type=KernelEventType.TURN_END,
                content="Parked for operator approval (appr_child_2).",
                is_finished=True,
            )

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=ParkAgainKernel(),
    )
    parent_id = "sess_root_park2"
    child_id = f"{parent_id}_child_ffff0000"
    store.create_session(agent_id="assistant", title="Parent", session_id=parent_id)
    result = await engine.resume_nested_child(
        child_session_id=child_id,
        parent_session_id=parent_id,
        agent_id="specialist-agent",
    )
    assert result["status"] == "approval_required"
    assert result["parked"]["approval_id"] == "appr_child_2"
    parent_tools = [m for m in store.get_messages(parent_id) if m.role == Role.TOOL]
    parked = json.loads(parent_tools[-1].content)
    assert parked["status"] == "approval_required"
    assert parked["approval_id"] == "appr_child_2"
    assert parked["tool_name"] == "cli_exec"


@pytest.mark.asyncio
async def test_handoff_applies_at_least_10_child_turns(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    kernel = StreamTurnKernel(content="ok")
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_budget_10",
        task_intent="Implement the card",
        depth=1,
    )
    assert envelope.max_turns == 10
    result = await engine.execute_handoff(envelope)
    assert result.status == "completed"
    assert kernel.max_turns == 10
    assert result.success is True


@pytest.mark.asyncio
async def test_handoff_provider_failure_text_maps_to_failed(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]
    kernel = StreamTurnKernel(
        content=(
            "All 1 candidate providers failed execution. "
            "(ollama: Failed to connect to Ollama at http://192.168.1.29:11434)"
        )
    )
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_provider_fail",
        task_intent="Implement CARD-001",
        depth=1,
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "failed"
    assert result.success is False
    assert "Failed to connect" in (result.error_message or "")


@pytest.mark.asyncio
async def test_handoff_timeout_text_maps_to_failed(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]
    kernel = StreamTurnKernel(content="Ollama timed out at http://192.168.1.29:11434: PoolTimeout")
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_timeout_fail",
        task_intent="Implement CARD-001",
        depth=1,
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "failed"
    assert result.success is False
    assert "timed out" in (result.error_message or "").lower()


@pytest.mark.asyncio
async def test_handoff_packet_is_child_user_message_not_parent_history(isolated_engine_setup):
    """Child user message is the packet only. Parent transcript never leaks [REQ-ORCH-036]."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]
    parent_id = "sess_parent_secret"
    store.create_session(agent_id="assistant", title="Parent", session_id=parent_id)
    store.save_message(
        session_id=parent_id,
        agent_id="assistant",
        message=ChatMessage(role=Role.USER, content="PARENT_SECRET_TRANSCRIPT_DO_NOT_LEAK"),
    )
    kernel = StreamTurnKernel(content="child-ok")
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    packet = HandoffPacket(
        goal="Write the script",
        facts=["repo is AutoReiv", "card is CARD-098"],
        constraints=["do not push"],
        done_when="tests green",
        budget={"max_turns": 10, "max_handoffs": 0, "max_ollama_slots": 1},
    )
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id=parent_id,
        task_intent="ignored when packet is set",
        context_payload={"history": ["PARENT_SECRET_TRANSCRIPT_DO_NOT_LEAK"], "messages": ["nope"]},
        packet=packet,
        depth=1,
    )
    result = await engine.execute_handoff(envelope)
    assert result.status == "completed"
    child_text = kernel.passed_user_content
    assert "Handoff Packet" in child_text
    assert "Write the script" in child_text
    assert "repo is AutoReiv" in child_text
    assert "do not push" in child_text
    assert "tests green" in child_text
    assert "PARENT_SECRET_TRANSCRIPT_DO_NOT_LEAK" not in child_text
    assert "ignored when packet is set" not in child_text
    child_id = kernel.passed_session_id
    child_msgs = store.get_messages(child_id)
    blob = " ".join(m.content or "" for m in child_msgs)
    assert "PARENT_SECRET_TRANSCRIPT_DO_NOT_LEAK" not in blob


def test_handoff_packet_missing_field_fails_closed():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        HandoffPacket(goal="only-goal")
    with pytest.raises(ValidationError):
        HandoffPacket.model_validate({"goal": "g", "facts": [], "constraints": [], "done_when": "d"})


@pytest.mark.asyncio
async def test_handoff_missing_packet_field_fails_closed(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]
    kernel = StreamTurnKernel(content="should-not-run")
    engine = HandoffIsolationEngine(agent_registry=registry, state_store=store, kernel=kernel)
    envelope = HandoffEnvelope(
        sender_agent_id="general-assistant",
        recipient_agent_id="specialist-agent",
        session_id="sess_bad_packet",
        task_intent="x",
        depth=1,
        packet=HandoffPacket(goal="g", facts=[], constraints=[], done_when="d", budget={}),
    )
    envelope.packet.goal = "   "
    result = await engine.execute_handoff(envelope)
    assert result.status == "failed"
    assert "goal" in (result.error_message or "").lower()
    assert kernel.stream_turn_called is False
