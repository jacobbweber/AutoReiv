"""
Unit tests for HandoffIsolationEngine kernel delegation and isolation guardrails [REQ-ORCH-003, REQ-A2A-003].
Verifies that HandoffIsolationEngine correctly dispatches to kernels implementing run_turn
(with fallback to execute_turn), handles event lifecycles, and enforces safety bounds.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.orchestration.models import HandoffEnvelope
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


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
async def test_handoff_delegates_to_run_turn(isolated_engine_setup):
    """Verify that HandoffIsolationEngine invokes run_turn on AgentKernel."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    class MockRunTurnKernel:
        def __init__(self):
            self.run_turn_called = False
            self.passed_agent = None
            self.passed_session_id = None
            self.passed_user_content = None

        async def run_turn(self, agent: AgentProfile, session_id: str, user_content: str = ""):
            self.run_turn_called = True
            self.passed_agent = agent
            self.passed_session_id = session_id
            self.passed_user_content = user_content
            return ChatMessage(
                role=Role.ASSISTANT,
                content="Diagnostics completed: CPU load 12%, Memory free 74%",
            )

    kernel = MockRunTurnKernel()
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
    assert kernel.run_turn_called is True
    assert kernel.passed_agent.id == "specialist-agent"
    assert kernel.passed_agent.max_turns == 3
    assert "sess_root_001_child_" in kernel.passed_session_id
    assert "Diagnose system load" in kernel.passed_user_content
    assert '"detail": "high"' in kernel.passed_user_content

    # Verify event notifications
    event_names = [e[0] for e in events]
    assert "handoff_start" in event_names
    assert "handoff_complete" in event_names


@pytest.mark.asyncio
async def test_handoff_fallback_to_execute_turn(isolated_engine_setup):
    """Verify that HandoffIsolationEngine falls back to execute_turn if run_turn is absent."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    class MockLegacyKernel:
        def __init__(self):
            self.execute_turn_called = False

        async def execute_turn(self, agent: AgentProfile, session_id: str, user_content: str = ""):
            self.execute_turn_called = True
            return MagicMock(content="Legacy kernel response", turns_taken=1)

    kernel = MockLegacyKernel()
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

    assert result.status == "completed"
    assert "Legacy kernel response" in result.summary
    assert kernel.execute_turn_called is True


@pytest.mark.asyncio
async def test_handoff_handles_kernel_exception_gracefully(isolated_engine_setup):
    """Verify that HandoffIsolationEngine catches kernel errors and returns failed status."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(side_effect=RuntimeError("Provider connection reset"))

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=mock_kernel,
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
    """Verify recursion depth > 2 is rejected."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock()

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=mock_kernel,
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
    mock_kernel.run_turn.assert_not_called()


@pytest.mark.asyncio
async def test_handoff_self_delegation_guardrail(isolated_engine_setup):
    """Verify circular self-handoff is rejected."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=MagicMock(),
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
    """Verify unknown specialist agent returns failed status."""
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=MagicMock(),
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

    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content=json.dumps(
                {
                    "status": "approval_required",
                    "approval_id": "appr_child_1",
                    "tool_name": "cli_exec",
                    "arguments": {"command": "ipconfig"},
                    "message": "Parked for operator approval (appr_child_1).",
                }
            ),
        )
    )
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel=mock_kernel,
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
async def test_handoff_passes_approval_mode_to_run_turn(isolated_engine_setup):
    registry = isolated_engine_setup["registry"]
    store = isolated_engine_setup["store"]

    class CaptureKernel:
        def __init__(self):
            self.kwargs = None

        async def run_turn(self, agent, session_id, user_content="", approval_mode="ask"):
            self.kwargs = {
                "session_id": session_id,
                "approval_mode": approval_mode,
            }
            return ChatMessage(role=Role.ASSISTANT, content="ok")

    kernel = CaptureKernel()
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
    from src.domain.kernel.models import KernelEvent, KernelEventType

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
    from src.domain.kernel.models import KernelEvent, KernelEventType

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
