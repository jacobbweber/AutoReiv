"""
Unit tests for DynamicSkillLoader & ScopedToolRegistry MCP Mounting [REQ-MCP-004, REQ-MCP-005].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile


def test_dynamic_skill_loader_parses_markdown_manual(tmp_path):
    skill_dir = tmp_path / "skills" / "weather_skill"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    content = """---
name: weather_lookup
description: Retrieve current weather metrics for a given city
author: AutoReiv
---

# Weather Lookup Skill
This skill provides real-time atmospheric readings.

```json
{
  "name": "get_current_weather",
  "description": "Fetch weather conditions",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {"type": "string"}
    },
    "required": ["city"]
  }
}
```
"""
    skill_md.write_text(content, encoding="utf-8")

    skills = DynamicSkillLoader.scan_skills_directory(str(tmp_path / "skills"))
    assert len(skills) == 1
    s = skills[0]
    assert s["name"] == "weather_lookup"
    assert len(s["tools"]) == 1
    assert s["tools"][0].name == "get_current_weather"


@pytest.mark.asyncio
async def test_scoped_tool_registry_mounts_mcp_tools():
    registry = ScopedToolRegistry()

    # Register dynamic MCP tool definitions and executor
    mcp_tool_def = ToolDefinition(
        name="mcp_git_status",
        description="Inspect git status",
        parameters={"type": "object"},
    )

    async def mock_mcp_executor(**kwargs) -> str:
        return "MCP executed mcp_git_status"

    registry.mount_mcp_tool(mcp_tool_def, mock_mcp_executor)

    agent = AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="General",
        system_prompt="Helpful",
        allowed_tool_names=["mcp_git_status"],
    )

    allowed = registry.get_tools_for_agent(agent)
    assert len(allowed) == 1
    assert allowed[0].name == "mcp_git_status"

    call = ToolCall(id="c1", name="mcp_git_status", arguments={})
    res = await registry.execute(call, agent)
    assert res.success is True
    assert res.output == "MCP executed mcp_git_status"
