"""Unit tests for built-in capability seeder [CARD-407, REQ-407-001].

Verifies that seed_builtin_capabilities populates capability_index with TrustTier.TRUSTED
for tools, agent profiles, and platform skills.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.capabilities.seeder import seed_builtin_capabilities
from src.domain.capabilities.models import CapabilityKind, TrustTier
from src.infrastructure.memory.repositories.capability_catalog import (
    CapabilityCatalogRepository,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def repo(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    return CapabilityCatalogRepository(store)


class DummyToolDef:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description


class DummySkill:
    def __init__(self, id: str, name: str, description: str, tools: list[str]):
        self.id = id
        self.name = name
        self.description = description
        self.tools = tools


class DummyProfile:
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        pack_tool_names: list[str],
        skills: list[DummySkill],
    ):
        self.id = id
        self.name = name
        self.description = description
        self.pack_tool_names = pack_tool_names
        self.skills = skills


def test_seed_builtin_capabilities_none_repo():
    count = seed_builtin_capabilities(None, None, None)
    assert count == 0


def test_seed_builtin_capabilities_populates_trusted_entries(repo):
    tool_reg = MagicMock()
    tool_reg.list_tools.return_value = [
        DummyToolDef("inspect_system_health", "Inspect AutoReiv runtime health"),
        DummyToolDef("wiki_note_create", "Create note in wiki"),
    ]

    agent_reg = MagicMock()
    skill_health = DummySkill(
        "platform-health",
        "Platform Health",
        "Telemetry and health",
        ["inspect_system_health"],
    )
    autoreiv_profile = DummyProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Autonomous platform assistant",
        pack_tool_names=["inspect_system_health", "wiki_note_create"],
        skills=[skill_health],
    )
    agent_reg.list_agents.return_value = [autoreiv_profile]

    user_catalog = MagicMock()
    user_catalog.list_skill_metadata.return_value = [
        {
            "id": "wiki-curation",
            "title": "Wiki Curation",
            "description": "Curate inbox notes",
            "pack_id": "librarian",
            "origin": "platform",
        }
    ]

    seeded = seed_builtin_capabilities(repo, tool_reg, agent_reg, user_catalog)
    assert seeded >= 4

    # Verify tool entry
    tool_entry = repo.get_entry("tool.inspect_system_health")
    assert tool_entry is not None
    assert tool_entry.kind == CapabilityKind.TOOL
    assert tool_entry.trust_tier == TrustTier.TRUSTED
    assert "autoreiv" in tool_entry.roles

    # Verify agent entry
    agent_entry = repo.get_entry("agent.autoreiv")
    assert agent_entry is not None
    assert agent_entry.kind == CapabilityKind.AGENT
    assert agent_entry.trust_tier == TrustTier.TRUSTED

    # Verify skills entries
    skill_entry = repo.get_entry("skill.platform-health")
    assert skill_entry is not None
    assert skill_entry.kind == CapabilityKind.SKILL
    assert skill_entry.trust_tier == TrustTier.TRUSTED

    wiki_skill = repo.get_entry("skill.wiki-curation")
    assert wiki_skill is not None
    assert wiki_skill.trust_tier == TrustTier.TRUSTED

    # Verify resolver matches when trusted_only=True
    resolver = CapabilityCatalogResolver(repo)
    result = resolver.resolve("inspect system health", trusted_only=True)
    assert len(result.matched) > 0
    matched_ids = [m.id for m in result.matched]
    assert any("health" in mid for mid in matched_ids)

