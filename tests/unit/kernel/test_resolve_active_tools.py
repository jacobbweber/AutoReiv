"""Rule of 7 entropy budget clamps active tools to at most 8 [CARD-362, ADR-0054]."""

from unittest.mock import MagicMock

from src.application.kernel.agent_kernel import MAX_ACTIVE_TOOLS_PER_TURN, AgentKernel
from src.domain.gateway.models import ToolDefinition
from src.domain.kernel.models import AgentProfile


def test_resolve_active_tools_enforces_rule_of_7_ceiling():
    tools = [
        ToolDefinition(name=f"tool_{i}", description=f"Tool {i}", parameters={"type": "object", "properties": {}})
        for i in range(12)
    ]
    registry = MagicMock()
    registry.get_tools_for_agent.return_value = tools
    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=MagicMock(),
        telemetry=MagicMock(),
    )
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="Test",
        system_prompt="Test",
        allowed_tool_names=[t.name for t in tools],
        max_active_tools=6,
    )
    resolved = kernel._resolve_active_tools(agent, user_content="unrelated query")
    assert len(resolved) == MAX_ACTIVE_TOOLS_PER_TURN
    assert len(resolved) == 8
    assert {t.name for t in resolved}.issubset({t.name for t in tools})
