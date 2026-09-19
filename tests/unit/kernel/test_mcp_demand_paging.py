"""
Unit tests for CARD-377 Phase 2: Dynamic MCP Capability Discovery & Demand Paging.
[REQ-MCP-HANDSHAKE-004..006]
"""

from unittest.mock import MagicMock

from src.application.kernel.agent_kernel import MAX_ACTIVE_TOOLS_PER_TURN, AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.platform_primitives import PlatformPrimitiveTools
from src.domain.gateway.models import ToolDefinition
from src.domain.kernel.models import AgentProfile


def test_dynamic_capability_index_lists_mounted_mcp_servers():
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
        allowed_skill=["wiki", "coding", "diagnostics", "tasks"],
    )

    sys_msg = kernel._build_effective_system_message(agent, user_content="hello")
    content = sys_msg.content

    # Baseline platform skills must be present
    assert "wiki" in content
    assert "coding" in content
    assert "diagnostics" in content
    assert "tasks" in content
    # Dynamic MCP server must be in the index
    assert "blender" in content
    assert "2 tools" in content or "Blender MCP server" in content


def test_match_intent_skills_matches_mcp_server_names():
    """Verify _match_intent_skills matches MCP server names when provided or discovered [REQ-MCP-HANDSHAKE-005]."""
    # Statically without extra domains
    assert AgentKernel._match_intent_skills("inspect blender scene") == []

    # With extra domains / discovered MCP servers
    matched = AgentKernel._match_intent_skills("can you inspect the blender scene?", extra_domains=["blender"])
    assert "blender" in matched


def test_activate_skill_activates_mcp_tool_family():
    """Verify activate_skill activates MCP tool family when present in registry [REQ-MCP-HANDSHAKE-005]."""
    registry = ScopedToolRegistry()
    registry.mount_mcp_tool(
        name="mcp_blender_execute_script",
        definition=ToolDefinition(name="mcp_blender_execute_script", description="Execute script", parameters={"type": "object"}),
        handler=MagicMock(),
    )
    registry.mount_mcp_tool(
        name="mcp_blender_get_scene_info",
        definition=ToolDefinition(name="mcp_blender_get_scene_info", description="Get scene", parameters={"type": "object"}),
        handler=MagicMock(),
    )

    primitives = PlatformPrimitiveTools(state_store=MagicMock())
    primitives.register_tools(registry)

    result = primitives.activate_skill(["blender"])
    assert result["status"] == "activated"
    assert "blender" in result["activated_skills"]
    assert "mcp_blender_execute_script" in result["activated_tools"]
    assert "mcp_blender_get_scene_info" in result["activated_tools"]


def test_get_tools_for_agent_resolves_active_mcp_skills():
    """Verify ScopedToolRegistry returns MCP tools for autoreiv when active_skills includes the server [REQ-MCP-HANDSHAKE-006]."""
    registry = ScopedToolRegistry()
    registry.mount_mcp_tool(
        name="mcp_blender_execute_script",
        definition=ToolDefinition(name="mcp_blender_execute_script", description="Execute script", parameters={"type": "object"}),
        handler=MagicMock(),
    )

    agent = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="Test",
    )

    # Inactive turn -> no blender tools
    inactive_tools = registry.get_tools_for_agent(agent, active_skills=[])
    inactive_names = [t.name for t in inactive_tools]
    assert "mcp_blender_execute_script" not in inactive_names

    # Active turn with blender -> blender tools mounted
    active_tools = registry.get_tools_for_agent(agent, active_skills=["blender"])
    active_names = [t.name for t in active_tools]
    assert "mcp_blender_execute_script" in active_names


def test_resolve_active_tools_prioritizes_mcp_tools_and_respects_cap():
    """Verify _resolve_active_tools gives Priority 0 to active MCP tools and respects MAX_ACTIVE_TOOLS_PER_TURN [REQ-MCP-HANDSHAKE-005]."""
    registry = ScopedToolRegistry()
    mcp_tools = [
        ToolDefinition(name=f"mcp_blender_tool_{i}", description=f"Blender Tool {i}", parameters={"type": "object"})
        for i in range(12)
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
    )

    resolved = kernel._resolve_active_tools(
        agent,
        user_content="execute script in blender",
        active_skills=["blender"],
    )

    assert len(resolved) == MAX_ACTIVE_TOOLS_PER_TURN
    resolved_names = [t.name for t in resolved]
    # The keyword-matched script tool must be prioritized in the active tools
    assert "mcp_blender_execute_script" in resolved_names
