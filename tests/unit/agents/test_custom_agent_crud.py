"""
Unit tests for SQLite Custom Agent CRUD & Scoped Tool Scoping [REQ-FORGE-003, REQ-FORGE-004].
"""

import tempfile
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_store.db"
        store = SQLiteStateStore(db_path=db_path)
        yield store






def test_builtin_agent_registry_loads_custom_agents(temp_store):
    """Verify BuiltinAgentRegistry merges built-ins and custom agents seamlessly."""
    tool_reg = ScopedToolRegistry()
    registry = BuiltinAgentRegistry(state_store=temp_store, master_tool_registry=tool_reg)

    # CARD-570: shipped agents come from platform/agents/*.md; no hard-coded builtins.
    agents = registry.list_agents()
    assert {"autoreiv", "developer", "direct", "tutor", "architect"} <= {a.id for a in agents}
    assert not any(a.id == "agent-builder" for a in agents)
    assert not any(a.id == "assistant" for a in agents)

    # Add custom agent via registry
    new_agent = AgentProfile(
        id="qa-tester",
        name="QA Tester",
        description="Integration test engineer",
        system_prompt="You write and verify integration tests.",
        purpose=ModelPurpose.REASONING,
        avatar_icon="check-circle",
        is_builtin=False,
    )
    registry.register_custom_agent(new_agent)

    # Verify presence in list and get
    agents_after = registry.list_agents()
    assert any(a.id == "qa-tester" for a in agents_after)
    fetched = registry.get_agent("qa-tester")
    assert fetched is not None
    assert fetched.name == "QA Tester"

    # Delete custom agent via registry
    res = registry.delete_custom_agent("qa-tester")
    assert res is True
    assert registry.get_agent("qa-tester") is None

    # Cannot delete built-in
    res_builtin = registry.delete_custom_agent("assistant")
    assert res_builtin is False
    res_autoreiv = registry.delete_custom_agent("autoreiv")
    assert res_autoreiv is False
