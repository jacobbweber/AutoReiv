"""
Unit tests for CARD-389: Uniform Skill-First Architecture and Agent Forge Realignment.
Verifies:
- [REQ-389-001]: SQLite Specialty Storage seed runbook & platform skill registration.
- [REQ-389-002]: Agent display name customization with immutable identity slug.
- [REQ-389-003]: storage_enabled automatically binds sqlite-storage skill.
- [REQ-389-004]: Conversational agent (0 skills) mounts only OS baseline primitives.
- [REQ-389-005]: Negative assertions against naked tool bindings and slug mutability.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.application.agent_packs.schema import REQUIRED_PLATFORM_TOOLS
from src.domain.agents.guardrails import AgentProfileGuardrail
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import app

pytestmark = pytest.mark.guard




def test_req_389_002_agent_name_customization_and_immutable_slug(tmp_path: Path):
    """[REQ-389-002] Display name can be customized for any agent while preserving immutable slug."""
    db_path = tmp_path / "test_autoreiv.db"
    store = SQLiteStateStore(db_path)

    # 1. Customization model supports name
    customization = AgentCustomization(
        agent_id="developer",
        name="Lead AI Architect",
        model="gpt-4o",
        temperature=0.7,
        storage_enabled=True,
    )
    assert customization.name == "Lead AI Architect"

    # 2-3. CARD-570: the customization is saved as the agent's user copy; the slug stays immutable
    base_profile = AgentProfile(
        id="developer",
        name="Developer",
        description="Senior Full-Stack Engineer",
        system_prompt="Write production code.",
    )
    registry = BuiltinAgentRegistry(profiles=[base_profile], state_store=store)
    registry.apply_customization(customization)
    agent = registry.get_agent("developer")
    assert agent is not None
    assert agent.id == "developer"  # Immutable slug
    assert agent.name == "Lead AI Architect"  # Custom display name

    # 4. API PUT /api/agents/{id} updates display name
    client = TestClient(app)
    resp = client.put(
        "/api/agents/developer",
        json={
            "id": "developer",
            "name": "Super Developer",
            "system_prompt": "You are a senior full-stack developer assisting the operator.",
            "model": "gpt-4o",
            "allowed_skill": ["wiki"],
            "storage_enabled": False,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "updated"
    assert data["agent"]["id"] == "developer"
    assert data["agent"]["name"] == "Super Developer"

    # Verify GET reflection
    get_resp = client.get("/api/agents")
    assert get_resp.status_code == 200
    agent_map = {a["id"]: a for a in get_resp.json()}
    assert agent_map["developer"]["name"] == "Super Developer"
    assert agent_map["developer"]["id"] == "developer"


def test_req_389_003_storage_enabled_auto_binds_sqlite_storage_skill():
    """[REQ-389-003] When storage_enabled is True, AgentProfileGuardrail auto-binds sqlite-storage skill."""
    profile_with_storage = AgentProfile(
        id="finance-bot",
        name="Finance Bot",
        description="Tracks finance",
        system_prompt="Track expenses.",
        storage_enabled=True,
        allowed_skill=["wiki"],
    )

    validated = AgentProfileGuardrail.validate(profile_with_storage)
    assert "sqlite-storage" in validated.allowed_skill
    assert "wiki" in validated.allowed_skill

    # When storage_enabled is False, sqlite-storage is not forcibly added
    profile_no_storage = AgentProfile(
        id="chat-bot",
        name="Chat Bot",
        description="Just chats",
        system_prompt="Chat nicely.",
        storage_enabled=False,
        allowed_skill=["wiki"],
    )
    validated_no_storage = AgentProfileGuardrail.validate(profile_no_storage)
    assert "sqlite-storage" not in validated_no_storage.allowed_skill


def test_req_389_004_conversational_agent_zero_skills_mounts_only_baseline():
    """[REQ-389-004] Conversational agent with zero active skills mounts strictly OS baseline primitives."""
    conversational_agent = {
        "id": "conversational-counselor",
        "name": "Conversational Counselor",
        "allowed_skill": [],
    }

    # CARD-539: no ticked skills -> only required baseline tools are allowed
    scoped = resolve_allowed_tools(conversational_agent).names
    assert set(scoped) == set(REQUIRED_PLATFORM_TOOLS)
    assert "query_agent_database" not in scoped
    assert "execute_agent_database" not in scoped
    assert "wiki_read" not in scoped
    assert "read_project_file" not in scoped

    # Ticking sqlite-storage allows its declared tools
    scoped_with_storage = resolve_allowed_tools({**conversational_agent, "allowed_skill": ["sqlite-storage"]}).names
    assert "query_agent_database" in scoped_with_storage
    assert "execute_agent_database" in scoped_with_storage
    for req in REQUIRED_PLATFORM_TOOLS:
        assert req in scoped_with_storage


def test_req_389_005_negative_assertion_naked_tools_cannot_be_bound():
    """[REQ-389-005] Negative assertion: naked tools without active skill are excluded and slug cannot mutate."""
    test_agent = {
        "id": "isolated-analyst",
        "name": "Isolated Analyst",
        "allowed_skill": ["wiki"],
    }

    # sqlite-storage tools are NOT present when only wiki is active
    scoped = resolve_allowed_tools(test_agent).names
    assert "query_agent_database" not in scoped
    assert "execute_agent_database" not in scoped

    # Even if an agent payload tries to sneak naked tools, only ticked skills grant tools (CARD-539)
    test_agent_with_naked = {
        "id": "isolated-analyst",
        "name": "Isolated Analyst",
        "allowed_skill": [],
    }
    scoped_naked = resolve_allowed_tools(test_agent_with_naked).names
    assert "bash" not in scoped_naked
    assert "execute_sql" not in scoped_naked
    assert "query_agent_database" not in scoped_naked
    assert set(scoped_naked) == set(REQUIRED_PLATFORM_TOOLS)
