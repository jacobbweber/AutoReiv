"""CARD-539 / ADR-0061: resolve_allowed_tools is the only decider of an agent's tools.

REQ-539-001: allowed = REQUIRED_PLATFORM_TOOLS + tools bound to ticked skills (D1: SQLite rows win).
"""

from __future__ import annotations

import json

import pytest

from src.application.agent_packs.allowed_tools import resolve_allowed_tools, skill_tools
from src.application.agent_packs.schema import REQUIRED_PLATFORM_TOOLS
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.skill_bindings import SkillToolBindingRepository


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "ops.db"
    data = tmp_path / "data"
    (data / "packs").mkdir(parents=True)
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    return SkillToolBindingRepository(db_path=str(db)), data


def _agent(agent_id="a539", **kw):
    return AgentProfile(id=agent_id, name="A", description="d", system_prompt="p", **kw)


def test_required_plus_ticked_skill_tools_only(env):
    allowed = resolve_allowed_tools(_agent(allowed_skill=["wiki-knowledge"]))
    assert set(REQUIRED_PLATFORM_TOOLS) <= allowed.names
    assert {"wiki_note_search", "wiki_note_read", "wiki_note_list"} <= allowed.names
    assert "wiki_note_create" not in allowed.names


def test_read_document_file_is_a_required_platform_tool_d3(env):
    assert "read_document_file" in REQUIRED_PLATFORM_TOOLS
    assert "read_document_file" in resolve_allowed_tools(_agent()).names


def test_legacy_tool_lists_grant_nothing(env):
    agent = _agent(
        allowed_skill=["wiki-knowledge"],
        allowed_tool_names=["get_weather", "execute_code"],
        pack_tool_names=["cli_exec"],
    )
    names = resolve_allowed_tools(agent).names
    assert not {"get_weather", "execute_code", "cli_exec"} & names


def test_profile_flags_grant_nothing_d2_d3(env):
    agent = _agent(storage_enabled=True, mcp_servers=[{"name": "srv", "transport": "stdio"}])
    allowed = resolve_allowed_tools(agent)
    assert "query_agent_database" not in allowed
    assert "mcp_srv_lookup" not in allowed


def test_storage_comes_from_the_sqlite_storage_tick(env):
    assert "query_agent_database" in resolve_allowed_tools(_agent(allowed_skill=["sqlite-storage"]))


def test_sqlite_binding_row_wins_over_seed_d1(env):
    repo, _ = env
    repo.replace("wiki-knowledge", ["wiki_note_read", "get_weather"])
    names = resolve_allowed_tools(_agent(allowed_skill=["wiki-knowledge"])).names
    assert {"wiki_note_read", "get_weather"} <= names
    assert "wiki_note_search" not in names
    assert skill_tools(["wiki-knowledge"])["wiki-knowledge"] == ["wiki_note_read", "get_weather"]


def test_pack_json_skill_tools_seed_when_no_row(env):
    _, data = env
    pack = data / "packs" / "a539"
    pack.mkdir()
    (pack / "pack.json").write_text(
        json.dumps({"id": "a539", "skills": [{"id": "weather-desk", "tools": ["get_weather"]}]}), encoding="utf-8"
    )
    assert "get_weather" in resolve_allowed_tools(_agent(allowed_skill=["weather-desk"]))
    assert "get_weather" not in resolve_allowed_tools(_agent(agent_id="other", allowed_skill=["weather-desk"]))


def test_repo_platform_pack_seed_covers_pack_only_skills(env):
    names = resolve_allowed_tools(_agent(agent_id="autoreiv", allowed_skill=["agent-authoring"])).names
    assert "inspect_agent_pack" in names


def test_mcp_wildcard_binding_matches_registered_names(env):
    repo, _ = env
    repo.replace("mcp-srv", ["mcp_srv_*"])
    allowed = resolve_allowed_tools(_agent(allowed_skill=["mcp-srv"]))
    assert "mcp_srv_lookup" in allowed
    assert "mcp_other_lookup" not in allowed


def test_direct_agent_has_no_tools(env):
    assert not resolve_allowed_tools(_agent(agent_id="direct", allowed_skill=["wiki-knowledge"])).names


def test_no_agent_id_special_case(env):
    ticks = ["wiki-knowledge", "platform-health"]
    assert resolve_allowed_tools(_agent("autoreiv", allowed_skill=ticks)).names == resolve_allowed_tools(
        _agent("custom-x", allowed_skill=ticks)
    ).names


def test_provenance_names_the_skill(env):
    allowed = resolve_allowed_tools(_agent(allowed_skill=["wiki-knowledge"]))
    assert "wiki-knowledge" in allowed.provenance["wiki_note_search"]
    assert allowed.provenance["activate_skill"] == ("platform",)


def test_skill_view_available_when_any_skill_is_ticked(env):
    assert "skill_view" in resolve_allowed_tools(_agent(allowed_skill=["wiki-knowledge"]))
    assert "skill_view" not in resolve_allowed_tools(_agent())
