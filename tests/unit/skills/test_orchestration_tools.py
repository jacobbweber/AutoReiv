"""
Unit tests for Orchestration Skill & Isolated Handoff Engine [REQ-ORCH-002, REQ-ORCH-003].
"""


import pytest

from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.skills.orchestration_tools import OrchestrationTools
from src.domain.orchestration.models import HandoffEnvelope
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_packs.catalog import platform_pack_profile


@pytest.fixture
def test_setup(tmp_path):
    db_path = tmp_path / "test_state.db"
    store = SQLiteStateStore(db_path=db_path)
    registry = BuiltinAgentRegistry(state_store=store)
    registry.register_profile(platform_pack_profile("assistant"))
    registry.register_profile(platform_pack_profile("autoreiv"))
    directory = AgentDirectoryService(agent_registry=registry, state_store=store)

    from src.domain.kernel.models import KernelEvent, KernelEventType

    class MockStreamKernel:
        def __init__(self):
            self.stream_calls = []

        async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
            self.stream_calls.append(
                {"agent": agent, "session_id": session_id, "user_content": user_content, "approval_mode": approval_mode}
            )
            yield KernelEvent(event_type=KernelEventType.TOKEN, content="Subagent completed task successfully")
            yield KernelEvent(
                event_type=KernelEventType.TURN_END,
                content="Subagent completed task successfully",
                is_finished=True,
            )

    mock_kernel = MockStreamKernel()

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel_factory=lambda profile: mock_kernel,
    )

    skill = OrchestrationTools(
        directory_service=directory,
        handoff_engine=engine,
        caller_agent_id="assistant",
        session_id="sess_root_001",
    )

    return {
        "store": store,
        "registry": registry,
        "directory": directory,
        "engine": engine,
        "skill": skill,
        "mock_kernel": mock_kernel,
    }


def test_lookup_agents_tool(test_setup):
    """Verify lookup_agents tool returns compact agent summaries [REQ-A2A-002]."""
    skill = test_setup["skill"]
    res = skill.lookup_agents("platform diagnostics telemetry autoreiv")
    assert "autoreiv" in res.lower()
    assert len(res) < 1000  # Compact token footprint


@pytest.mark.asyncio
async def test_handoff_to_agent_success(test_setup):
    """Verify successful handoff to valid specialist subagent [REQ-A2A-002, REQ-A2A-003]."""
    skill = test_setup["skill"]
    res = await skill.handoff_to_agent(
        target_agent_id="autoreiv",
        task_directive="Inspect system disk usage and free memory",
        input_payload={"threshold": 80},
    )

    assert "Subagent completed task successfully" in res
    assert "status: completed" in res.lower() or "completed" in res.lower()


@pytest.mark.asyncio
async def test_handoff_anti_recursion_depth_limit(test_setup):
    """Verify delegation beyond depth 2 is rejected [REQ-A2A-003]."""
    engine = test_setup["engine"]
    envelope = HandoffEnvelope(
        sender_agent_id="assistant",
        recipient_agent_id="autoreiv",
        session_id="sess_123",
        task_intent="Nested task",
        depth=3,  # Exceeds max depth 2
    )

    result = await engine.execute_handoff(envelope)
    assert result.status == "rejected"
    assert "recursion" in result.error_message.lower() or "depth" in result.error_message.lower()


@pytest.mark.asyncio
async def test_handoff_blocks_self_delegation(test_setup):
    """Verify circular self-handoff is rejected [REQ-A2A-003]."""
    skill = test_setup["skill"]  # caller is 'assistant'
    res = await skill.handoff_to_agent(
        target_agent_id="assistant",
        task_directive="Looping to self",
    )

    assert "rejected" in res.lower() or "forbidden" in res.lower() or "self" in res.lower()


@pytest.mark.asyncio
async def test_handoff_to_non_existent_agent(test_setup):
    """Verify delegation to unknown agent fails gracefully [REQ-A2A-003]."""
    skill = test_setup["skill"]
    res = await skill.handoff_to_agent(
        target_agent_id="quantum-physicist-agent-999",
        task_directive="Compute quantum state",
    )

    assert "not found" in res.lower() or "failed" in res.lower()


@pytest.mark.asyncio
async def test_handoff_uses_live_tool_context(test_setup):
    from src.application.kernel.tool_registry import _tool_context

    skill = test_setup["skill"]
    mock_kernel = test_setup["mock_kernel"]
    token = _tool_context.set({"agent_id": "assistant", "session_id": "chat_sess_live"})
    try:
        res = await skill.handoff_to_agent(
            target_agent_id="autoreiv",
            task_directive="List system info",
        )
    finally:
        _tool_context.reset(token)

    assert "completed" in res.lower()
    assert mock_kernel.stream_calls
    assert mock_kernel.stream_calls[0]["session_id"].startswith("chat_sess_live_child_")


@pytest.mark.asyncio
async def test_handoff_bubbles_child_approval(test_setup):
    from src.domain.kernel.models import KernelEvent, KernelEventType

    class ParkKernel:
        async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
            yield KernelEvent(
                event_type=KernelEventType.APPROVAL_REQUIRED,
                content="Parked for operator approval (appr_child_1).",
                approval_id="appr_child_1",
                tool_call={"id": "c1", "name": "cli_exec", "arguments": {"command": "ipconfig"}},
            )
            yield KernelEvent(
                event_type=KernelEventType.TURN_END,
                content="Parked for operator approval (appr_child_1).",
                is_finished=True,
            )

    skill = test_setup["skill"]
    skill.handoff_engine.kernel = ParkKernel()
    skill.handoff_engine.kernel_factory = lambda profile: ParkKernel()
    res = await skill.handoff_to_agent(
        target_agent_id="autoreiv",
        task_directive="List system info using cli_exec",
    )
    assert isinstance(res, dict)
    assert res["status"] == "approval_required"
    assert res["approval_id"] == "appr_child_1"
    assert res["tool_name"] == "cli_exec"
    assert res["arguments"]["command"] == "ipconfig"


@pytest.mark.asyncio
async def test_handoff_batch_over_cap_errors(test_setup):
    skill = test_setup["skill"]
    res = await skill.handoff_to_agent(
        target_agent_id="autoreiv",
        batch=[
            {"target_agent_id": "autoreiv", "task_directive": "one"},
            {"target_agent_id": "autoreiv", "task_directive": "two"},
        ],
    )
    assert "failed" in res.lower()
    assert "exceeds" in res.lower()
    assert "not truncated" in res.lower()


@pytest.mark.asyncio
async def test_handoff_packet_missing_field_fails(test_setup):
    skill = test_setup["skill"]
    res = await skill.handoff_to_agent(
        target_agent_id="autoreiv",
        packet={"goal": "only goal"},
    )
    assert "failed" in res.lower()
    assert "missing required fields" in res.lower()


@pytest.mark.asyncio
async def test_handoff_packet_coercion_resilience(test_setup):
    """Verify handoff packet coerces integer budget and list done_when seamlessly without failing."""
    skill = test_setup["skill"]
    res = await skill.handoff_to_agent(
        target_agent_id="autoreiv",
        packet={
            "goal": "Run diagnostics",
            "facts": ["Fact 1"],
            "constraints": ["Constraint 1"],
            "done_when": ["Diagnostics completed."],
            "budget": 3,
        },
    )
    assert "completed" in str(res).lower()
    assert "turns used" in str(res).lower()

