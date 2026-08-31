"""
Unit tests for SQLite Custom Agent CRUD & Scoped Tool Scoping [REQ-FORGE-003, REQ-FORGE-004].
"""

import tempfile
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_store.db"
        store = SQLiteStateStore(db_path=db_path)
        yield store


def test_sqlite_custom_agent_crud(temp_store):
    """Test full CRUD operations for custom agent profiles in SQLiteStateStore."""
    custom = AgentProfile(
        id="devops-sre",
        name="DevOps SRE",
        description="Kubernetes & CI/CD Specialist",
        system_prompt="You automate pipelines and monitor K8s clusters.",
        purpose=ModelPurpose.TASK_EXECUTION,
        tone=AgentTone.TECHNICAL,
        avatar_icon="shield",
        model="default",
        allowed_tool_names=["system_info", "cli_exec"],
        max_turns=12,
        is_builtin=False,
    )

    # 1. Create
    temp_store.save_agent_profile(custom)

    # 2. Read
    fetched = temp_store.get_agent_profile("devops-sre")
    assert fetched is not None
    assert fetched.id == "devops-sre"
    assert fetched.name == "DevOps SRE"
    assert fetched.purpose == ModelPurpose.TASK_EXECUTION
    assert fetched.tone == AgentTone.TECHNICAL
    assert fetched.avatar_icon == "shield"
    assert fetched.allowed_tool_names == ["system_info", "cli_exec"]
    assert fetched.max_turns == 12
    assert fetched.is_builtin is False

    # 3. List
    all_custom = temp_store.list_custom_agent_profiles()
    assert len(all_custom) == 1
    assert all_custom[0].id == "devops-sre"

    # 4. Update
    custom.name = "DevOps SRE Lead"
    custom.max_turns = 15
    temp_store.save_agent_profile(custom)
    updated = temp_store.get_agent_profile("devops-sre")
    assert updated.name == "DevOps SRE Lead"
    assert updated.max_turns == 15

    # 5. Delete
    deleted = temp_store.delete_agent_profile("devops-sre")
    assert deleted is True
    assert temp_store.get_agent_profile("devops-sre") is None


def test_builtin_agents_cannot_be_deleted(temp_store):
    """Verify built-in agents cannot be deleted from store."""
    deleted = temp_store.delete_agent_profile("assistant")
    assert deleted is False
    deleted_auto = temp_store.delete_agent_profile("autoreiv")
    assert deleted_auto is False
    deleted_coding = temp_store.delete_agent_profile("coding")
    assert deleted_coding is False


def test_builtin_agent_registry_loads_custom_agents(temp_store):
    """Verify BuiltinAgentRegistry merges built-ins and custom agents seamlessly."""
    tool_reg = ScopedToolRegistry()
    registry = BuiltinAgentRegistry(state_store=temp_store, master_tool_registry=tool_reg)

    # Remaining builtin is hidden Agent Builder. Assistant/AutoReiv load via platform packs on bootstrap.
    agents = registry.list_agents()
    assert len(agents) == 1
    assert any(a.id == "agent-builder" for a in agents)
    assert not any(a.id == "assistant" for a in agents)
    assert not any(a.id == "autoreiv" for a in agents)
    assert not any(a.id == "coding" for a in agents)
    assert not any(a.id == "conductor" for a in agents)
    assert not any(a.id == "review" for a in agents)

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
    res_coding = registry.delete_custom_agent("coding")
    assert res_coding is False
