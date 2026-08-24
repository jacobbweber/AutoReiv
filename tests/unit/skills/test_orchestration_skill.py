"""
Unit tests for Orchestration Skill & Isolated Handoff Engine [REQ-ORCH-002, REQ-ORCH-003].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.skills.orchestration_skill import OrchestrationSkill
from src.domain.orchestration.models import HandoffEnvelope
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def test_setup(tmp_path):
    db_path = tmp_path / "test_state.db"
    store = SQLiteStateStore(db_path=db_path)
    registry = BuiltinAgentRegistry(state_store=store)
    directory = AgentDirectoryService(agent_registry=registry, state_store=store)

    # Mock kernel or child executor
    mock_kernel = MagicMock()
    mock_kernel.run_turn = AsyncMock(return_value=MagicMock(content="Subagent completed task successfully", turns_taken=2))
    mock_kernel.execute_turn = mock_kernel.run_turn

    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel_factory=lambda profile: mock_kernel,
    )

    skill = OrchestrationSkill(
        directory_service=directory,
        handoff_engine=engine,
        caller_agent_id="general-assistant",
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
    res = skill.lookup_agents("linux sysadmin shell")
    assert "linux-sysadmin" in res or "sysadmin" in res.lower()
    assert len(res) < 1000  # Compact token footprint


@pytest.mark.asyncio
async def test_handoff_to_agent_success(test_setup):
    """Verify successful handoff to valid specialist subagent [REQ-A2A-002, REQ-A2A-003]."""
    skill = test_setup["skill"]
    res = await skill.handoff_to_agent(
        target_agent_id="linux-sysadmin",
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
        sender_agent_id="general-assistant",
        recipient_agent_id="linux-sysadmin",
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
    skill = test_setup["skill"]  # caller is 'general-assistant'
    res = await skill.handoff_to_agent(
        target_agent_id="general-assistant",
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
