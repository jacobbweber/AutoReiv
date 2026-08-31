"""
Unit tests for AgentBuilderTools [REQ-FORGE-005].
"""

import tempfile
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.domain.settings.models import ModelPurpose
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
    assert "propose_agent_specification" in tool_names
    assert "save_agent_specification" in tool_names
    assert "propose_skill" in tool_names
    assert "propose_tool" in tool_names
    assert "propose_workflow" in tool_names
    assert "commit_skill_pack" in tool_names


@pytest.mark.asyncio
async def test_list_available_skills_and_tools(builder_setup):
    skill, agent_reg, tool_reg = builder_setup
    skill.register_tools(tool_reg)

    result = await skill.list_available_skills_and_tools()
    assert "tools" in result
    assert "purposes" in result
    assert "tones" in result


@pytest.mark.asyncio
async def test_propose_agent_specification(builder_setup):
    skill, agent_reg, tool_reg = builder_setup

    spec = await skill.propose_agent_specification(
        role="PostgreSQL Database Administrator",
        objective="Optimize slow queries, manage indexes, and review schema migrations.",
        domain="database",
    )

    assert "id" in spec
    assert "name" in spec
    assert "system_prompt" in spec
    assert "purpose" in spec
    assert spec["purpose"] in [p.value for p in ModelPurpose]


@pytest.mark.asyncio
async def test_save_agent_specification(builder_setup):
    skill, agent_reg, tool_reg = builder_setup

    spec = {
        "id": "postgres-dba",
        "name": "Postgres DBA",
        "description": "Database Optimization Specialist",
        "system_prompt": "You are AutoReiv's Postgres DBA. Optimize queries and analyze schemas.",
        "purpose": "task_execution",
        "tone": "technical",
        "avatar_icon": "database",
        "allowed_tool_names": [],
        "max_turns": 10,
    }

    res = await skill.save_agent_specification(spec)
    assert res["status"] == "created"
    assert res["id"] == "postgres-dba"
    assert res.get("sprawl_warning")
    assert "postgres-dba" in res["sprawl_warning"]

    # Verify presence in agent registry
    saved = agent_reg.get_agent("postgres-dba")
    assert saved is not None
    assert saved.name == "Postgres DBA"


@pytest.mark.asyncio
async def test_propose_descriptions_are_recommend_not_pack_birth(builder_setup):
    skill, agent_reg, tool_reg = builder_setup
    skill.register_tools(tool_reg)
    by_name = {t.name: t.description.lower() for t in tool_reg.list_tools()}
    assert "do not use this to create the agent" in by_name["propose_agent_specification"]
    assert "i am ready to create a new agent" in by_name["propose_agent_specification"]
    assert "scaffold_agent_pack is the write" in by_name["save_agent_specification"]
    assert "recommend-capability only" in by_name["propose_tool"]
    assert "not pack birth" in by_name["propose_tool"]
    assert "recommend-capability only" in by_name["propose_skill"]
    assert "recommend-capability only" in by_name["propose_workflow"]
