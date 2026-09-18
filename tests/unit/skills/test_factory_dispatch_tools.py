"""Tests for FactoryDispatchTools: inspect_agent_pack and launch_factory_training [CARD-355, REQ-FACT-061, REQ-FACT-062]."""

from unittest.mock import MagicMock

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.factory_dispatch_tools import FactoryDispatchTools
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def mock_store(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test_store.db"))
    store.initialize_db()
    return store


@pytest.fixture
def mock_agent_registry():
    registry = MagicMock(spec=BuiltinAgentRegistry)

    # Mock agent profile
    mock_profile = MagicMock()
    mock_profile.id = "test-agent"
    mock_profile.name = "Test Agent"
    mock_profile.description = "A test agent"
    mock_profile.pack_tool_names = ["read_file", "write_file"]
    mock_profile.allowed_skill = ["filesystem"]
    mock_profile.skills = [MagicMock(id="filesystem", tools=["read_file", "write_file"])]

    registry.get_profile.side_effect = lambda ag_id: mock_profile if ag_id == "test-agent" else None
    registry.get_agent.side_effect = lambda ag_id: mock_profile if ag_id == "test-agent" else None
    registry.list_agents.return_value = ["autoreiv", "developer", "test-agent"]
    return registry



@pytest.fixture
def dispatch_tools(mock_agent_registry, mock_store, tmp_path):
    tool_reg = ScopedToolRegistry()
    tools = FactoryDispatchTools(
        agent_registry=mock_agent_registry,
        store=mock_store,
        data_dir=tmp_path / "data",
    )
    tools.register_tools(tool_reg)
    return tools, tool_reg


@pytest.mark.asyncio
async def test_inspect_agent_pack_success(dispatch_tools):
    tools, _ = dispatch_tools
    res = await tools.inspect_agent_pack(agent_id="test-agent")
    assert res["success"] is True
    assert res["agent_id"] == "test-agent"
    assert res["name"] == "Test Agent"
    assert "read_file" in res["tools"]
    assert "write_file" in res["tools"]
    assert "filesystem" in res["skills"]


@pytest.mark.asyncio
async def test_inspect_agent_pack_not_found(dispatch_tools):
    tools, _ = dispatch_tools
    res = await tools.inspect_agent_pack(agent_id="nonexistent-agent")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


@pytest.mark.asyncio
async def test_launch_factory_training_validation_error(dispatch_tools):
    tools, _ = dispatch_tools
    # Missing target agent
    res = await tools.launch_factory_training(
        target_agent_id="",
        seed_intent="Add hyperv tool",
        objectives=["List VMs"],
    )
    assert res["success"] is False
    assert "target_agent_id" in res["error"].lower()

    # Missing both intent and objectives
    res2 = await tools.launch_factory_training(
        target_agent_id="test-agent",
        seed_intent="",
        objectives=[],
    )
    assert res2["success"] is False
    assert "intent or at least one objective" in res2["error"].lower()


@pytest.mark.asyncio
async def test_launch_factory_training_success(dispatch_tools, mock_store):
    tools, _ = dispatch_tools
    res = await tools.launch_factory_training(
        target_agent_id="test-agent",
        seed_intent="Add Hyper-V snapshot tool",
        objectives=["Create named checkpoint", "Restore named checkpoint"],
        deliverable_type="tool",
        reference_docs="PowerShell Hyper-V cmdlet manual",
        risk_policy="ask",
    )
    assert res["success"] is True
    assert res["status"] == "queued"
    assert res["target_agent_id"] == "test-agent"
    assert res["job_id"].startswith("fjob_")
