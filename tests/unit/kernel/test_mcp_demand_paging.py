"""
Unit tests for CARD-377 Phase 2: Dynamic MCP Capability Discovery & Demand Paging.
[REQ-MCP-HANDSHAKE-004..006]
CARD-539 D2: an MCP server reaches an agent only through a ticked skill that binds its tools.
CARD-578: a ticked MCP skill sends all its tools; no intent matching, activation or cap.
"""

from unittest.mock import MagicMock

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ToolDefinition
from src.domain.kernel.models import AgentProfile


def test_domain_line_lists_the_ticked_mcp_skill(bind_skills):
    """Verify system message capability index dynamically includes mounted MCP server [REQ-MCP-HANDSHAKE-004]."""
    registry = ScopedToolRegistry()
    registry.mount_mcp_tool(
        name="mcp_blender_execute_script",
        definition=ToolDefinition(name="mcp_blender_execute_script", description="Execute Python script in Blender", parameters={"type": "object"}),
        handler=MagicMock(),
    )
    registry.mount_mcp_tool(
        name="mcp_blender_get_scene_info",
        definition=ToolDefinition(name="mcp_blender_get_scene_info", description="Get scene hierarchy", parameters={"type": "object"}),
        handler=MagicMock(),
    )

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="You are AutoReiv Core.",
        allowed_skill=["diagnostics"] + bind_skills({"mcp-blender": ["mcp_blender_*"]}),
    )

    content = kernel._build_effective_system_message(agent, user_content="hello").content
    assert "## Your domain" in content
    assert "Mcp Blender" in content  # label generated from the ticked skill id
    tools = {t.name for t in registry.get_tools_for_agent(agent)}
    assert {"mcp_blender_execute_script", "mcp_blender_get_scene_info"} <= tools


def test_get_tools_for_agent_includes_mcp_tools_only_when_their_skill_is_ticked(bind_skills):
    """Verify ScopedToolRegistry returns MCP tools for autoreiv only when a ticked skill binds the server [REQ-MCP-HANDSHAKE-006]."""
    registry = ScopedToolRegistry()
    registry.mount_mcp_tool(
        name="mcp_blender_execute_script",
        definition=ToolDefinition(name="mcp_blender_execute_script", description="Execute script", parameters={"type": "object"}),
        handler=MagicMock(),
    )

    unticked = AgentProfile(id="autoreiv", name="AutoReiv", description="Platform Agent", system_prompt="Test")
    assert "mcp_blender_execute_script" not in [t.name for t in registry.get_tools_for_agent(unticked)]

    ticked = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="Test",
        allowed_skill=bind_skills({"mcp-blender": ["mcp_blender_*"]}),
    )
    assert "mcp_blender_execute_script" in [t.name for t in registry.get_tools_for_agent(ticked)]


def test_resolve_active_tools_sends_every_tool_of_a_ticked_mcp_skill(bind_skills):
    """CARD-578: all 21 tools of the ticked MCP skill are sent, whatever the question [REQ-MCP-HANDSHAKE-005]."""
    registry = ScopedToolRegistry()
    mcp_tools = [
        ToolDefinition(name=f"mcp_blender_tool_{i}", description=f"Blender Tool {i}", parameters={"type": "object"})
        for i in range(20)
    ]
    # Add a specific script tool to test keyword relevance
    script_tool = ToolDefinition(name="mcp_blender_execute_script", description="Execute python script in Blender", parameters={"type": "object"})
    mcp_tools.append(script_tool)

    for t in mcp_tools:
        registry.mount_mcp_tool(name=t.name, definition=t, handler=MagicMock())

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="Test",
        allowed_skill=bind_skills({"mcp-blender": ["mcp_blender_*"]}),
    )

    for question in ("execute script in blender", "hi"):
        resolved_names = {t.name for t in kernel._resolve_active_tools(agent, user_content=question)}
        assert {t.name for t in mcp_tools} <= resolved_names, question
