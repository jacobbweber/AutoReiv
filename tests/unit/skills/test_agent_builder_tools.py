"""
Unit tests for AgentBuilderTools [REQ-FORGE-005].
"""

import tempfile
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def builder_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_builder.db"
        store = SQLiteStateStore(db_path=db_path)
        tool_reg = ScopedToolRegistry()
        agent_reg = BuiltinAgentRegistry(state_store=store, master_tool_registry=tool_reg)
        skill = AgentBuilderTools(agent_registry=agent_reg, tool_registry=tool_reg, store=store)
        yield skill, agent_reg, tool_reg


@pytest.mark.asyncio
async def test_agent_builder_tools_registration(builder_setup):
    skill, agent_reg, tool_reg = builder_setup
    skill.register_tools(tool_reg)

    tools = tool_reg.list_tools()
    tool_names = [t.name for t in tools]
    assert "list_available_skills_and_tools" in tool_names
    assert "propose_agent_specification" not in tool_names
    assert "save_agent_specification" not in tool_names
    assert "propose_skill" in tool_names
    assert "propose_tool" in tool_names
    assert "propose_workflow" not in tool_names
    assert "commit_skill" in tool_names


@pytest.mark.asyncio
async def test_list_available_skills_and_tools(builder_setup):
    skill, agent_reg, tool_reg = builder_setup
    skill.register_tools(tool_reg)

    result = await skill.list_available_skills_and_tools()
    # CARD-539 item 9: an authoring catalog, marked not callable, never a tool list.
    assert "catalog_tools" in result and "skills" in result and "tools" not in result
    assert "not callable" in result["note"]
    assert "purposes" in result
    assert "tones" in result


@pytest.mark.asyncio
async def test_propose_descriptions_are_recommend_not_agent_creation(builder_setup):
    skill, agent_reg, tool_reg = builder_setup
    skill.register_tools(tool_reg)
    by_name = {t.name: t.description.lower() for t in tool_reg.list_tools()}
    assert "propose_agent_specification" not in by_name
    assert "save_agent_specification" not in by_name
    assert "recommend-capability only" in by_name["propose_tool"]
    assert "not agent creation" in by_name["propose_tool"]
    assert "recommend-capability only" in by_name["propose_skill"]
    assert "propose_workflow" not in by_name
