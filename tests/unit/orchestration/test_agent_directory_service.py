"""
Unit tests for Agent Directory Service [REQ-ORCH-001].
"""

import pytest

from src.application.orchestration.directory_service import AgentDirectoryService
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def directory_service(tmp_path):
    db_path = tmp_path / "test_state.db"
    state_store = SQLiteStateStore(db_path=db_path)
    registry = BuiltinAgentRegistry(state_store=state_store)
    return AgentDirectoryService(agent_registry=registry, state_store=state_store)


def test_discover_builtin_agents(directory_service):
    """Verify built-in agents are discoverable by capability keywords [REQ-A2A-001]."""
    # Search for platform SRE capabilities
    results = directory_service.search_agents(query="diagnostics platform logs telemetry autoreiv", limit=3)
    assert len(results) >= 1
    assert any(a.id == "autoreiv" for a in results)

    # Search for workflow assistant capabilities
    results = directory_service.search_agents(query="assistant workflow tasks daily", limit=3)
    assert len(results) >= 1
    assert any(a.id == "assistant" for a in results)


def test_discover_custom_agent(directory_service, tmp_path):
    """Verify custom SQLite agents created via Agent Forge are dynamically indexed [REQ-A2A-001]."""
    # Create a custom agent profile in SQLite
    custom_profile = AgentProfile(
        id="postgres-dba",
        name="Postgres DBA Specialist",
        description="Postgres tuning and queries",
        system_prompt="You specialize in PostgreSQL query tuning, indexes, and database migrations.",
        tone=AgentTone.TECHNICAL,
        purpose=ModelPurpose.TASK_EXECUTION,
        allowed_tool_names=["execute_sql", "explain_query"],
        max_turns=10,
        is_builtin=False,
    )
    directory_service.state_store.save_agent_profile(custom_profile)

    results = directory_service.search_agents(query="postgresql database query tuning", limit=3)
    assert len(results) >= 1
    assert any(a.id == "postgres-dba" for a in results)

    # Check compact card representation
    dba_card = next(a for a in results if a.id == "postgres-dba")
    assert dba_card.name == "Postgres DBA Specialist"
    assert "postgresql" in dba_card.summary.lower() or "database" in dba_card.summary.lower()


def test_compact_agent_card_token_efficiency(directory_service):
    """Verify search returns compact cards without leaking full system prompts [REQ-A2A-001]."""
    results = directory_service.search_agents(query="admin", limit=5)
    for card in results:
        assert len(card.summary) <= 200
        assert card.id
        assert card.name
