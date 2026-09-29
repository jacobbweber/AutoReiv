"""CARD-539 / ADR-0061: resolve_allowed_tools is the only decider of an agent's tools.

REQ-539-001: allowed = REQUIRED_PLATFORM_TOOLS + tools named by ticked skills (CARD-570: the SKILL.md ``tools:`` list).
"""

from __future__ import annotations

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools, skill_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.domain.kernel.models import AgentProfile
from src.infrastructure.content.store import configure
from tests.unit.agent_skills.catalog import pack_dict

pytestmark = pytest.mark.guard


@pytest.fixture
def env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    store = configure(data)
    return store, data


def _user_skill(data, skill_id, tools):
    d = data / "skills" / skill_id
    d.mkdir(parents=True)
    tl = "".join(f"  - {t}\n" for t in tools)
    (d / "SKILL.md").write_text(f"---\nname: {skill_id}\ndescription: d\ntools:\n{tl}---\nbody\n", encoding="utf-8")


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


def test_user_copy_tools_win_over_shipped_d1(env):
    store, _ = env
    store.set_skill_tools("wiki-knowledge", ["wiki_note_read", "get_weather"])
    names = resolve_allowed_tools(_agent(allowed_skill=["wiki-knowledge"])).names
    assert {"wiki_note_read", "get_weather"} <= names
    assert "wiki_note_search" not in names
    assert skill_tools(["wiki-knowledge"])["wiki-knowledge"] == ["wiki_note_read", "get_weather"]


def test_user_skill_file_tools_grant(env):
    _, data = env
    _user_skill(data, "weather-desk", ["get_weather"])
    assert "get_weather" in resolve_allowed_tools(_agent(allowed_skill=["weather-desk"]))
    assert "get_weather" not in resolve_allowed_tools(_agent(allowed_skill=[]))


def test_shipped_skill_tools_come_from_platform_skills(env):
    names = resolve_allowed_tools(_agent(agent_id="autoreiv", allowed_skill=["agent-authoring"])).names
    assert "inspect_agent" in names


def test_mcp_wildcard_binding_matches_registered_names(env):
    _, data = env
    _user_skill(data, "mcp-srv", ["mcp_srv_*"])
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
    assert allowed.provenance["ask_clarification"] == ("platform",)
    assert "activate_skill" not in allowed.names  # CARD-578: removed


def test_skill_view_available_when_any_skill_is_ticked(env):
    assert "skill_view" in resolve_allowed_tools(_agent(allowed_skill=["wiki-knowledge"]))
    assert "skill_view" not in resolve_allowed_tools(_agent())


def test_autoreiv_pack_prompt_stores_no_static_domain_list():
    """D5: the domain comes from ticked skills at runtime; the pack prompt must not pin a fixed list
    (live QA: AutoReiv quoted the fixed list and ignored an accepted get-weather skill)."""

    prompt = pack_dict("autoreiv")["system_prompt"]
    section = prompt.split("[DOMAIN BOUNDARIES & REFUSALS]", 1)[1].split("\n\n", 1)[0]
    assert "Focus on" not in section
    assert "Your domain" in section
