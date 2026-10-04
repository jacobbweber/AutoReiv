"""CARD-545 (ADR-0061 D11): native tools declare risk at registration.

A read-only native tool runs with no approval card; a write tool still asks; Jacob's tool_policy still wins.
"""

from __future__ import annotations

import pytest
import yaml

from src.application.agent_skills.tool_attachment import ATTACH_TOOL_PROPOSAL, apply_tool_attachment
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.application.skills.native_tool_engineering import NativeToolEngineeringTools
from src.application.tools.native_packaging import NATIVE_MANAGED_CONFIRM_KEY, NativeCustomToolService, NativeToolError
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.content.store import configure
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

GOOD = "def run(city='', **kw):\n    return {'city': city, 'temp_c': 20}\n"
SCHEMA = {"type": "object", "properties": {"city": {"type": "string"}}}


class _Agents:
    def __init__(self):
        self.saved = {}
        self.base = AgentProfile(id="autoreiv", name="AutoReiv", description="d", system_prompt="p", allowed_skill=[])

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
    agents = _Agents()
    gate = ToolPolicyGate(store)
    hitl = HITLApprovalEngine(store)
    service = NativeCustomToolService(
        store=store, tool_registry=registry, agent_registry=agents, policy_gate=gate, hitl_engine=hitl
    )
    return store, registry, agents, service, data, gate, hitl


def _raw(name, **extra):
    body = {
        "name": name,
        "description": f"CARD-545 {name}",
        "code": GOOD,
        "parameters": SCHEMA,
        "target_agent_id": "autoreiv",
    }
    body.update(extra)
    return body


def _accept(store, agents, registry, data, tool):
    pending = [
        p
        for p in store.get_pending_approvals(agent_id="autoreiv")
        if p["tool_name"] == ATTACH_TOOL_PROPOSAL and p["arguments"]["tool"] == tool
    ]
    return apply_tool_attachment(store, agents, registry, pending[0]["arguments"], data_root=data)


def _verdict(gate, registry, agents, tool):
    gate.reload_policy()
    return gate.evaluate(
        ToolCall(id="c1", name=tool, arguments={"city": "Paris"}),
        agents.get_agent("autoreiv"),
        registry_tool_names={d.name for d in registry.list_tools()},
        tool_risk=registry.get_tool_risk(tool),
    )


async def _ready(env, name, **extra):
    store, registry, agents, service, data, *_ = env
    body = await service.register(_raw(name, **extra))
    service.enable_by_operator(name)
    _accept(store, agents, registry, data, name)
    return body


async def test_read_only_tool_runs_without_an_approval_card(env):
    store, registry, agents, service, data, gate, hitl = env
    body = await _ready(env, "c545_weather", risk="read_only")
    assert body["risk"] == "read_only" and body["requires_hitl"] is False and body["risk_level"] == "low"
    assert registry.get_tool_risk("c545_weather") == "read_only"
    assert "c545_weather" not in (store.get_setting("tool_policy") or {}).get("require_confirm_tools", [])
    assert "c545_weather" not in hitl.high_risk_tools
    decision = _verdict(gate, registry, agents, "c545_weather")
    assert decision.verdict == ToolPolicyVerdict.ALLOW, decision.reason


async def test_write_tool_still_asks_even_with_requires_hitl_false(env):
    store, registry, agents, service, data, gate, hitl = env
    body = await _ready(env, "c545_save", risk="write")
    assert body["requires_hitl"] is True
    assert _verdict(gate, registry, agents, "c545_save").verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    await _ready(env, "c545_post", risk="network", requires_hitl=False)
    decision = _verdict(gate, registry, agents, "c545_post")
    assert decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    assert decision.policy_source == "declared_risk"


async def test_undeclared_and_destructive_tools_ask(env):
    *_, service, _data, _gate, _hitl = env
    legacy = await service.register(_raw("c545_legacy"))
    assert legacy["risk"] == "" and legacy["requires_hitl"] is True
    wipe = await service.register(_raw("c545_wipe", risk="destructive", requires_hitl=False, target_agent_id=""))
    assert wipe["requires_hitl"] is True and wipe["risk_level"] == "high"


async def test_invalid_risk_is_refused(env):
    *_, service, _data, _gate, _hitl = env
    with pytest.raises(NativeToolError, match="risk must be read_only, write, network or destructive"):
        await service.register(_raw("c545_bad", risk="harmless"))
    with pytest.raises(NativeToolError, match="read_only tool cannot have risk_level high"):
        await service.register(_raw("c545_bad2", risk="read_only", risk_level="high"))


async def test_jacobs_tool_policy_still_overrides(env):
    store, registry, agents, service, data, gate, _hitl = env
    await _ready(env, "c545_weather", risk="read_only")
    policy = dict(store.get_setting("tool_policy") or {})
    policy["require_confirm_tools"] = list(policy.get("require_confirm_tools") or []) + ["c545_weather"]
    store.set_setting("tool_policy", policy)
    assert _verdict(gate, registry, agents, "c545_weather").verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    # A later save of the same read-only tool does not remove the entry Jacob added.
    await service.register(_raw("c545_weather", risk="read_only"))
    assert "c545_weather" in store.get_setting("tool_policy")["require_confirm_tools"]
    # safe_tools lets a write tool run without asking.
    await _ready(env, "c545_save", risk="write")
    policy = dict(store.get_setting("tool_policy"))
    policy["safe_tools"] = ["c545_save"]
    store.set_setting("tool_policy", policy)
    assert _verdict(gate, registry, agents, "c545_save").verdict == ToolPolicyVerdict.ALLOW


async def test_relaxing_an_enabled_tool_needs_jacob_again(env):
    store, registry, agents, service, data, gate, _hitl = env
    await _ready(env, "c545_lookup", risk="write")
    assert "c545_lookup" in registry
    body = await service.register(_raw("c545_lookup", risk="read_only"))  # same code, lower risk
    assert body["approval"] == "disabled" and body["mounted"] is False
    assert "no longer asks before each call, so Jacob must enable it again" in body["message"]
    assert "c545_lookup" not in registry
    policy = store.get_setting("tool_policy")
    assert "c545_lookup" not in policy["require_confirm_tools"]  # the service added it, so it removes it
    assert "c545_lookup" not in policy[NATIVE_MANAGED_CONFIRM_KEY]
    service.enable_by_operator("c545_lookup")
    assert _verdict(gate, registry, agents, "c545_lookup").verdict == ToolPolicyVerdict.ALLOW


async def test_tightening_an_enabled_tool_keeps_it_enabled(env):
    store, registry, agents, service, *_ = env
    await _ready(env, "c545_lookup", risk="read_only")
    body = await service.register(_raw("c545_lookup", risk="write"))
    assert body["approval"] == "enabled" and body["mounted"] is True
    assert registry.get_tool_risk("c545_lookup") == "write"


async def test_new_skill_copies_the_tools_risk_into_frontmatter(env):
    store, registry, agents, service, data, *_ = env
    await _ready(env, "c545_weather", risk="read_only")
    await _ready(env, "c545_save", risk="write")
    for sid, read_only, hitl in (("c545-weather", True, False), ("c545-save", False, True)):
        text = (data / "skills" / sid / "SKILL.md").read_text(encoding="utf-8")
        meta = yaml.safe_load(text.split("---", 2)[1])
        assert meta["safety"]["read_only"] is read_only and meta["safety"]["requires_hitl"] is hitl


async def test_delete_drops_the_policy_entry(env):
    store, *_rest = env
    service = env[3]
    await service.register(_raw("c545_save", risk="write", target_agent_id=""))
    assert "c545_save" in store.get_setting("tool_policy")["require_confirm_tools"]
    service.delete("c545_save")
    assert "c545_save" not in store.get_setting("tool_policy")["require_confirm_tools"]


def test_developer_tool_schema_declares_risk():
    reg = ScopedToolRegistry()
    NativeToolEngineeringTools().register_tools(reg)
    definition = reg.get_tool_definition("register_native_tool")
    risk = definition.parameters["properties"]["risk"]
    assert risk["enum"] == ["read_only", "write", "network", "destructive"]
    assert "read_only" in definition.description and "ask before each call" in definition.description


def test_router_defaults_leave_hitl_to_the_declared_risk():
    from src.web.routers.native_tools import NativeToolRegisterRequest

    body = NativeToolRegisterRequest(name="x", description="d", code=GOOD).model_dump()
    assert body["requires_hitl"] is None and body["risk"] == "" and body["risk_level"] == ""
