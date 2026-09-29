"""CARD-537 D1 (Jacob, 2026-09-26): an accepted skill tool widens the agent's domain.

REQ-537-001: after Jacob accepts an "attach tool to skill" proposal, the skill's tools are in the agent's domain and
the generated domain line names the skill. REQ-537-002: the domain line routes, it never tells the model to refuse.
REQ-537-003: the next turn sees the acceptance, in an existing chat and a new chat (a fresh registry read).
End to end through the real pieces: NativeCustomToolService.register -> pending proposal -> apply_tool_attachment
-> resolve_allowed_tools / domain_line / the kernel's per-turn tool list.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import domain_line, resolve_allowed_tools
from src.application.agent_skills.tool_attachment import ATTACH_TOOL_PROPOSAL, apply_tool_attachment
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.tools.native_packaging import NativeCustomToolService
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import pack_dict

CODE = "def run(port='', **kw):\n    return {'port': port or 'Boston', 'high_tide': '14:05'}\n"
SCHEMA = {"type": "object", "properties": {"port": {"type": "string"}}}
QUESTION = "What time is high tide at Boston harbor today?"
REFUSAL = re.compile(r"outside (of )?my (authorized )?domain|not authorized to|\brefuse|unable to help", re.I)


_SAVED: dict = {}


class _Agents:
    """Like BuiltinAgentRegistry: a saved agent file wins; a new instance = a fresh read (new chat)."""

    def __init__(self, store):
        self.store = store

    def get_agent(self, agent_id):
        if agent_id != "autoreiv":
            return None
        if agent_id in _SAVED:
            return _SAVED[agent_id].model_copy(deep=True)
        return AgentProfile(id="autoreiv", name="AutoReiv", description="d", system_prompt="p",
                            allowed_skill=["wiki-knowledge"], is_builtin=True)

    def save_agent(self, profile, *, create=False):
        _SAVED[profile.id] = profile.model_copy(deep=True)
        return profile


@pytest.fixture
def env(tmp_path, monkeypatch):
    db, data = tmp_path / "s.db", tmp_path / "data"
    data.mkdir()
    _SAVED.clear()
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    registry = ScopedToolRegistry()
    for name in ("wiki_note_search", "wiki_note_read", "wiki_note_list", "system_info"):
        registry.register_tool(name, f"{name.replace('_', ' ')} for the wiki and what it holds", SCHEMA, lambda **kw: "ok")
    service = NativeCustomToolService(store=store, tool_registry=registry, agent_registry=_Agents(store))
    return store, registry, service, data


async def _register_and_propose(store, service):
    await service.register({
        "name": "c537_harbor_tide", "description": "Returns today's high tide time for a harbor port.",
        "code": CODE, "parameters": SCHEMA, "requires_hitl": False, "risk_level": "low",
        "target_agent_id": "autoreiv", "sample_arguments": {"port": "Boston"},
    })
    service.enable_by_operator("c537_harbor_tide")  # CARD-570: Jacob enables the runtime tool
    pending = [p for p in store.get_pending_approvals(agent_id="autoreiv") if p["tool_name"] == ATTACH_TOOL_PROPOSAL]
    assert len(pending) == 1
    return pending[0]


def _turn_tools(registry, store, agent, question=QUESTION):
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=registry, state_store=MagicMock(get_setting=MagicMock(return_value=None)),
                         telemetry=MagicMock())
    return [t.name for t in kernel._resolve_active_tools(agent, user_content=question)]


async def test_before_acceptance_the_tool_is_outside_the_domain(env):
    store, registry, service, _ = env
    await _register_and_propose(store, service)
    agent = _Agents(store).get_agent("autoreiv")
    assert "c537_harbor_tide" not in resolve_allowed_tools(agent)
    assert "c537_harbor_tide" not in _turn_tools(registry, store, agent)
    assert "tide" not in domain_line(agent).lower()


async def test_accepting_widens_the_domain_line_and_the_next_turn_in_a_new_chat(env):
    store, registry, service, data = env
    record = await _register_and_propose(store, service)
    agents = _Agents(store)
    out = apply_tool_attachment(store, agents, registry, record["arguments"], data_root=data)
    assert out["ticked"] is True

    fresh = _Agents(store).get_agent("autoreiv")  # REQ-537-003: a fresh read, like the next turn or a new chat
    assert out["skill_id"] in fresh.allowed_skill
    assert "c537_harbor_tide" in resolve_allowed_tools(fresh)
    line = domain_line(fresh)
    assert "tide" in line.lower(), line  # REQ-537-001: the generated domain line names the accepted skill
    assert not REFUSAL.search(line) and "handoff_to_agent" in line and "Ask Developer" in line  # REQ-537-002
    names = _turn_tools(registry, store, fresh)
    assert set(names) == set(resolve_allowed_tools(fresh)) & set(registry._tools)  # CARD-578: all at once
    assert "c537_harbor_tide" in names, names


@pytest.mark.parametrize("skill_id", ["autoreiv", "developer", "tutor"])
def test_no_platform_pack_pins_a_fixed_domain_that_would_hide_an_accepted_skill(skill_id):
    """Scavenger Pass (CARD-537): D1 holds for every agent. A hand-written "Focus strictly on ..." boundary
    contradicts an accepted skill tool; the boundary must point at the generated "Your domain" line and route."""

    prompt = pack_dict(skill_id)["system_prompt"]
    if "[DOMAIN BOUNDARIES & REFUSALS]" not in prompt:
        return
    section = prompt.split("[DOMAIN BOUNDARIES & REFUSALS]", 1)[1].split("\n\n", 1)[0]
    assert "Focus strictly" not in section and "Focus on" not in section, section
    assert "Your domain" in section and "handoff_to_agent" in section, section
