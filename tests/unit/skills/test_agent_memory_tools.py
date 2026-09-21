"""
Unit tests for Agent Cognitive Memory Tools [CARD-116, CARD-405].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.memory.agent_memory_tools import AgentMemoryTools
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


@pytest.mark.asyncio
async def test_agent_memory_tools_registration_and_execution(tmp_path):
    registry = ScopedToolRegistry()
    mem_tools = AgentMemoryTools(data_dir=tmp_path)
    mem_tools.register_tools(registry)

    # 1. Verify tools are registered
    assert "memorize_fact" in registry
    assert "recall_agent_memory" in registry

    # 2. Agent profile with memory enabled
    agent = AgentProfile(
        id="developer",
        name="Developer",
        description="Platform developer",
        system_prompt="You are developer.",
        memory_enabled=True,
        allowed_tool_names=["read_project_file", "recall_agent_memory", "memorize_fact"],
    )

    authorized = registry.get_tools_for_agent(agent)
    tool_names = [t.name for t in authorized]
    assert "memorize_fact" in tool_names
    assert "recall_agent_memory" in tool_names

    # 3. Execute memorize_fact
    mem_call = ToolCall(
        id="call_1",
        name="memorize_fact",
        arguments={
            "entity": "user",
            "attribute": "test_runner",
            "value": "pytest -v",
            "category": "user_pref",
        },
    )
    result = await registry.execute(mem_call, agent)
    assert result.error is None
    assert result.output.get("status") == "ok"
    assert result.output.get("action_taken") == "ADD"

    # 4. Verify fact in physical DB
    repo = AgentMemoryRepository(agent_id="developer", data_dir=tmp_path)
    facts = repo.list_semantic_facts()
    assert len(facts) == 1
    assert facts[0]["attribute"] == "test_runner"
    assert facts[0]["value"] == "pytest -v"

    # 5. Execute recall_agent_memory
    recall_call = ToolCall(
        id="call_2",
        name="recall_agent_memory",
        arguments={"query": "test_runner"},
    )
    recall_res = await registry.execute(recall_call, agent)
    assert recall_res.error is None
    assert recall_res.output.get("status") == "ok"
    recalled_facts = recall_res.output.get("facts") or []
    assert len(recalled_facts) >= 1
    assert recalled_facts[0]["value"] == "pytest -v"
