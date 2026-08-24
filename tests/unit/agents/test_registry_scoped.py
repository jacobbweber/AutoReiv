"""
Unit tests for BuiltinAgentRegistry.get_scoped_registry_for_agent [REQ-AGENTS-001, REQ-KERNEL-002].
Verifies that tool registries are strictly scoped to an agent's authorized tool whitelist.
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile, AgentTone
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def master_registry_setup(tmp_path):
    db_path = tmp_path / "test_reg_scoped.db"
    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    master_tools = ScopedToolRegistry()

    def dummy_system_info():
        return {"os": "linux", "cores": 8}

    def dummy_cli_exec(cmd: str):
        return f"Executed {cmd}"

    def dummy_task_create(title: str):
        return f"Created task: {title}"

    def dummy_wiki_note(path: str):
        return f"Note: {path}"

    master_tools.register_tool(
        name="system_info",
        description="Get system information",
        parameters={"type": "object", "properties": {}},
        handler=dummy_system_info,
    )
    master_tools.register_tool(
        name="cli_exec",
        description="Execute a CLI command",
        parameters={"type": "object", "properties": {"cmd": {"type": "string"}}},
        handler=dummy_cli_exec,
    )
    master_tools.register_tool(
        name="task_tracker_create",
        description="Create a task",
        parameters={"type": "object", "properties": {"title": {"type": "string"}}},
        handler=dummy_task_create,
    )
    master_tools.register_tool(
        name="wiki_note_create",
        description="Create a wiki note",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        handler=dummy_wiki_note,
    )

    registry = BuiltinAgentRegistry(
        state_store=store,
        master_tool_registry=master_tools,
    )

    return {
        "store": store,
        "master_tools": master_tools,
        "registry": registry,
    }


def test_get_scoped_registry_filters_authorized_tools(master_registry_setup):
    """Verify that scoped registry contains only the agent's authorized tools."""
    registry = master_registry_setup["registry"]

    agent = AgentProfile(
        id="sysadmin-specialist",
        name="Sysadmin Specialist",
        description="Linux sysadmin",
        system_prompt="Manage linux servers",
        tone=AgentTone.TECHNICAL,
        allowed_tool_names=["system_info", "cli_exec"],
    )

    scoped = registry.get_scoped_registry_for_agent(agent)

    # Must contain exactly the authorized tools
    assert "system_info" in scoped._tools
    assert "cli_exec" in scoped._tools
    assert "task_tracker_create" not in scoped._tools
    assert "wiki_note_create" not in scoped._tools
    assert len(scoped._tools) == 2


@pytest.mark.asyncio
async def test_scoped_tool_execution(master_registry_setup):
    """Verify tools in scoped registry can be executed correctly via ScopedToolRegistry.execute."""
    registry = master_registry_setup["registry"]

    agent = AgentProfile(
        id="task-master",
        name="Task Master",
        description="Manages tasks",
        system_prompt="Create and track tasks",
        tone=AgentTone.CONCISE,
        allowed_tool_names=["task_tracker_create"],
    )

    scoped = registry.get_scoped_registry_for_agent(agent)
    assert "task_tracker_create" in scoped._tools

    # Execute authorized tool call
    call = ToolCall(id="call_001", name="task_tracker_create", arguments={"title": "Deploy update"})
    result = await scoped.execute(call, agent)
    assert result.success is True
    assert result.output == "Created task: Deploy update"
    assert result.error is None

    # Unauthorized tool call
    unauth_call = ToolCall(id="call_002", name="cli_exec", arguments={"cmd": "rm -rf /"})
    unauth_res = await scoped.execute(unauth_call, agent)
    assert unauth_res.success is False
    assert "not authorized" in unauth_res.error.lower()


def test_get_scoped_registry_unrestricted_agent(master_registry_setup):
    """Verify that an agent with empty allowed_tool_names gets master registry."""
    registry = master_registry_setup["registry"]
    master_tools = master_registry_setup["master_tools"]

    agent_default = AgentProfile(
        id="default-agent",
        name="Default Agent",
        description="Unrestricted agent",
        system_prompt="Omnipotent",
        tone=AgentTone.DEFAULT,
    )
    scoped_default = registry.get_scoped_registry_for_agent(agent_default)
    assert scoped_default is master_tools

    agent_empty = AgentProfile(
        id="empty-agent",
        name="Empty Agent",
        description="Empty tool list",
        system_prompt="None",
        tone=AgentTone.DEFAULT,
        allowed_tool_names=[],
    )
    scoped_empty = registry.get_scoped_registry_for_agent(agent_empty)
    assert scoped_empty is master_tools


def test_scoped_registry_ignores_nonexistent_tool_names(master_registry_setup):
    """Verify requesting non-existent tool names does not cause errors."""
    registry = master_registry_setup["registry"]

    agent = AgentProfile(
        id="custom-agent",
        name="Custom Agent",
        description="Custom tools",
        system_prompt="Custom",
        tone=AgentTone.FRIENDLY,
        allowed_tool_names=["system_info", "non_existent_tool_xyz"],
    )

    scoped = registry.get_scoped_registry_for_agent(agent)
    assert "system_info" in scoped._tools
    assert "non_existent_tool_xyz" not in scoped._tools
    assert len(scoped._tools) == 1
