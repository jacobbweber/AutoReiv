"""CARD-539 / ADR-0061 rule 8: Developer growth is a proposal, never a direct grant.

REQ-539-007 (pending proposal, no permission change until accepted),
REQ-539-008 (accepted = the skill's SKILL.md tools list + visible tick; CARD-570).
"""

from __future__ import annotations

import pytest

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.application.agent_packs.tool_attachment import (
    ATTACH_TOOL_PROPOSAL,
    apply_tool_attachment,
    propose_tool_attachment,
)
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.tools.developer_mediation import format_developer_prompt
from src.application.tools.native_packaging import NativeCustomToolService, NativeToolError
from src.domain.kernel.models import AgentProfile
from src.infrastructure.content.store import configure
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

GOOD = "def run(city='', **kw):\n    return {'city': city, 'temp_c': 20}\n"
SCHEMA = {"type": "object", "properties": {"city": {"type": "string"}}}


class _Agents:
    """Registry stub: a saved agent file wins, like BuiltinAgentRegistry.get_agent."""

    def __init__(self, store):
        self.store = store
        self.saved = {}
        self.base = AgentProfile(
            id="autoreiv", name="AutoReiv", description="d", system_prompt="p",
            allowed_skill=["wiki-knowledge"],
        )

    def get_agent(self, agent_id):
        if agent_id != "autoreiv":
            return None
        return (self.saved.get(agent_id) or self.base).model_copy(deep=True)

    def save_agent(self, profile, *, create=False):
        self.saved[profile.id] = profile.model_copy(deep=True)
        return profile


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "s.db"
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    configure(data)
    registry = ScopedToolRegistry()
    agents = _Agents(store)
    service = NativeCustomToolService(store=store, tool_registry=registry, agent_registry=agents)
    return store, registry, agents, service, data


def _raw(name, **extra):
    body = {"name": name, "description": f"CARD-539 {name}", "code": GOOD, "parameters": SCHEMA,
            "requires_hitl": False, "risk_level": "low"}
    body.update(extra)
    return body


async def test_register_proposes_an_attachment_instead_of_granting(env):
    store, _, agents, service, _ = env
    body = await service.register(_raw("c539_weather", target_agent_id="autoreiv"))
    assert "granted_agent_ids" not in body
    assert agents.saved == {}
    assert "c539_weather" not in resolve_allowed_tools(agents.get_agent("autoreiv"))
    pending = store.get_pending_approvals(agent_id="autoreiv")
    assert [p["tool_name"] for p in pending] == [ATTACH_TOOL_PROPOSAL]
    args = pending[0]["arguments"]
    assert args["tool"] == "c539_weather" and args["agent_id"] == "autoreiv"
    assert args["new_skill"] is True and args["skill_id"] == "c539-weather"
    assert args["evidence"]["status"] == "passed"
    assert body["proposal"]["approval_id"] == pending[0]["id"]


async def test_grant_agent_ids_is_gone(env):
    *_, service, _ = env
    with pytest.raises(NativeToolError) as caught:
        await service.register(_raw("c539_old", grant_agent_ids=["autoreiv"]))
    assert "target_agent_id" in str(caught.value)


def test_accepting_a_new_skill_writes_runbook_binding_and_tick(env):
    store, registry, agents, _, data = env
    registry.register_tool("c539_weather", "weather", SCHEMA, lambda **kw: 1)
    approval_id = propose_tool_attachment(store, tool="c539_weather", agent_id="autoreiv", session_id="s1",
                                          description="Current weather for a city")
    record = store.get_approval(approval_id)
    out = apply_tool_attachment(store, agents, registry, record["arguments"], data_root=data)
    assert out["skill_id"] == "c539-weather" and out["ticked"] is True
    assert (data / "skills" / "c539-weather" / "SKILL.md").is_file()
    profile = agents.get_agent("autoreiv")
    assert "c539-weather" in profile.allowed_skill
    assert "c539_weather" in resolve_allowed_tools(profile)


def test_attaching_to_an_existing_ticked_skill_keeps_its_tools(env):
    store, registry, agents, _, data = env
    registry.register_tool("c539_weather", "weather", SCHEMA, lambda **kw: 1)
    approval_id = propose_tool_attachment(store, tool="c539_weather", agent_id="autoreiv", session_id="s1",
                                          skill_id="wiki-knowledge")
    args = store.get_approval(approval_id)["arguments"]
    assert args["new_skill"] is False
    apply_tool_attachment(store, agents, registry, args, data_root=data)
    names = resolve_allowed_tools(agents.get_agent("autoreiv")).names
    assert {"c539_weather", "wiki_note_search", "wiki_note_read", "wiki_note_list"} <= names


def test_developer_prompt_asks_for_a_proposal_not_a_grant():
    prompt = format_developer_prompt({"intent": "weather", "draft": {"tool_name": "get_weather", "target_agent_id": "autoreiv"}})
    assert "grant_agent_ids" not in prompt
    assert 'target_agent_id "autoreiv"' in prompt


def test_native_tool_engineering_schema_has_no_grant_field():
    from src.application.skills.native_tool_engineering import NativeToolEngineeringTools

    reg = ScopedToolRegistry()
    NativeToolEngineeringTools().register_tools(reg)
    props = reg.get_tool_definition("register_native_tool").parameters["properties"]
    assert "grant_agent_ids" not in props and "target_agent_id" in props
