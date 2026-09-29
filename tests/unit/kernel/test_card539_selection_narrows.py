"""CARD-539 / ADR-0061: every consumer uses resolve_allowed_tools and selection only narrows.

REQ-539-002 (tool list, _execute_inner and ToolPolicyGate agree; no agent-id special case),
REQ-539-003 (selection output is a subset of allowed; empty intersection -> required only),
REQ-539-004 (activate_skill refuses unticked skills), REQ-539-005 (catalog is agent-scoped, no scan cap),
REQ-539-006 (the model is never offered a tool it may not call).
Property tests use a seeded random generator (no new dependencies).
"""

from __future__ import annotations

import random
from unittest.mock import MagicMock

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.application.kernel.agent_kernel import MAX_ACTIVE_TOOLS_PER_TURN, AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.application.skills.platform_primitives import PlatformPrimitiveTools
from src.domain.capabilities.models import CapabilityIndexEntry
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile

pytestmark = pytest.mark.slow

SKILL_POOL = [
    "wiki-knowledge", "wiki-inbox", "wiki-curation", "wiki_tasks", "platform-health", "session-inspect",
    "coding", "coordination", "proposals", "worker", "sandbox", "sqlite-storage",
    "mcp-engineering", "native-tool-engineering", "capability-authoring", "agent-authoring",
]
WORDS = ["wiki", "notes", "health", "gpu", "code", "repo", "mcp", "server", "deploy", "native", "tool",
         "weather", "tasks", "schedule", "hello", "sandbox", "agent", "pack", "scaffold", "list"]
EXTRA_TOOLS = ["get_weather", "c520_catalog_dump", "mcp_srv_lookup", "cli_exec", "execute_code",
               "repo_file_write", "read_project_file", "wiki_graph"]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    reg = ScopedToolRegistry()
    names = set(EXTRA_TOOLS) | set(REQUIRED_PLATFORM_TOOLS) | {"skill_view", "list_user_skill_packs"}
    for skill in SKILL_POOL:
        names |= resolve_allowed_tools(_agent(allowed_skill=[skill])).names
    for name in sorted(names):
        reg.register_tool(name, f"{name.replace('_', ' ')} tool", {"type": "object", "properties": {}}, lambda **kw: "ok")
    store = MagicMock()
    store.get_setting.return_value = None
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=reg, state_store=store, telemetry=MagicMock())
    return reg, kernel, ToolPolicyGate(store)


def _agent(agent_id="a539", **kw):
    return AgentProfile(id=agent_id, name="A", description="d", system_prompt="p", **kw)


def _random_agent(rng):
    return _agent(
        agent_id=rng.choice(["autoreiv", "developer", "custom-x"]),
        allowed_skill=rng.sample(SKILL_POOL, rng.randint(0, 6)),
        storage_enabled=rng.random() < 0.5,
        mcp_servers=[{"name": "srv"}] if rng.random() < 0.5 else [],
    )


def test_selection_is_always_a_subset_of_allowed(env):
    reg, kernel, _ = env
    rng = random.Random(539)
    for _ in range(250):
        agent = _random_agent(rng)
        allowed = resolve_allowed_tools(agent).names
        text = " ".join(rng.sample(WORDS, rng.randint(0, 5)))
        ids = [f"tool.{n}" for n in rng.sample(sorted(reg._tools), rng.randint(0, 4))]
        ids += [f"skill.{s}" for s in rng.sample(SKILL_POOL, rng.randint(0, 2))]
        active = rng.sample(SKILL_POOL, rng.randint(0, 3))
        listed = {t.name for t in reg.get_tools_for_agent(agent)}
        assert listed <= allowed
        matched = kernel._match_intent_skills(text, agent=agent)
        assert set(matched) <= set(agent.allowed_skill)
        chosen = kernel._resolve_active_tools(agent, text, matched_capability_ids=ids or None, active_skills=active)
        names = {t.name for t in chosen}
        assert names <= allowed, (agent.id, agent.allowed_skill, names - allowed)
        assert len(names) <= MAX_ACTIVE_TOOLS_PER_TURN


def test_empty_capability_intersection_mounts_required_only(env):
    _, kernel, _ = env
    agent = _agent(allowed_skill=["wiki-knowledge"])
    chosen = kernel._resolve_active_tools(agent, "wiki notes", matched_capability_ids=["tool.not_allowed_here"])
    assert {t.name for t in chosen} <= set(REQUIRED_PLATFORM_TOOLS)


def test_tool_list_execute_and_gate_agree(env):
    reg, _, gate = env
    rng = random.Random(5390)
    for _ in range(40):
        agent = _random_agent(rng)
        allowed = resolve_allowed_tools(agent).names
        for name in sorted(reg._tools):
            verdict = gate.evaluate(ToolCall(id="c", name=name, arguments={}), agent, registry_tool_names=set(reg._tools))
            gate_allows = not (verdict.verdict == ToolPolicyVerdict.BLOCK and verdict.policy_source == "agent_allowlist")
            assert gate_allows == (name in allowed), (agent.id, name)


async def test_execute_refuses_what_ticks_do_not_allow_even_for_autoreiv(env):
    reg, _, _ = env
    autoreiv = _agent("autoreiv", allowed_skill=["wiki-knowledge"], allowed_tool_names=["get_weather"])
    for name in ("execute_code", "get_weather", "wiki_note_create"):
        res = await reg.execute(ToolCall(id="c", name=name, arguments={}), autoreiv)
        assert res.success is False and "not authorized" in (res.error or ""), name
    ok = await reg.execute(ToolCall(id="c", name="wiki_note_read", arguments={}), autoreiv)
    assert ok.success is True


def test_autoreiv_and_custom_agent_get_the_same_tool_list(env):
    reg, _, _ = env
    ticks = ["wiki-knowledge", "platform-health", "coding"]
    a = {t.name for t in reg.get_tools_for_agent(_agent("autoreiv", allowed_skill=ticks))}
    b = {t.name for t in reg.get_tools_for_agent(_agent("custom-x", allowed_skill=ticks))}
    assert a == b and "wiki_note_search" in a


def test_activate_skill_refuses_an_unticked_skill(env):
    reg, _, _ = env
    prim = PlatformPrimitiveTools(state_store=None, tool_registry=reg)
    token = _tool_context.set({"agent_id": "a539", "allowed_skill": ["wiki-knowledge"]})
    try:
        refused = prim.activate_skill(["sandbox", "wiki"])
        ok = prim.activate_skill(["wiki-knowledge"])
    finally:
        _tool_context.reset(token)
    assert refused["status"] == "refused"
    assert refused["activated_tools"] == [] and refused["activated_skills"] == []
    assert "not ticked" in refused["message"]
    assert ok["activated_skills"] == ["wiki-knowledge"]
    assert set(ok["activated_tools"]) == {"wiki_note_search", "wiki_note_read", "wiki_note_list", "wiki_graph"}


def test_intent_matcher_only_returns_ticked_skills(env):
    _, kernel, _ = env
    agent = _agent(allowed_skill=["wiki-knowledge"])
    assert kernel._match_intent_skills("search my wiki notes and check gpu health", agent=agent) == ["wiki-knowledge"]


class _Store:
    def __init__(self, entries):
        self.entries = entries

    def list_entries(self, *, kinds=None, trust_tier=None, limit=50, offset=0):
        return self.entries[offset : offset + limit]

    def count_entries(self):
        return len(self.entries)


def test_catalog_match_is_agent_scoped_and_uncapped():
    entries = [
        CapabilityIndexEntry(id=f"tool.filler_{i}", kind="tool", name=f"filler {i}", keywords=["weather"], trust_tier="trusted")
        for i in range(300)
    ]
    entries.append(CapabilityIndexEntry(id="tool.get_weather", kind="tool", name="get weather", keywords=["weather"], trust_tier="trusted"))
    result = CapabilityCatalogResolver(_Store(entries)).resolve(
        "weather in boston", trusted_only=True, allowed_ids={"tool.get_weather"}
    )
    assert [e.id for e in result.matched] == ["tool.get_weather"]


def test_list_available_skills_and_tools_does_not_offer_the_registry_as_callable(env):
    from src.application.skills.agent_builder_tools import AgentBuilderTools

    reg, _, _ = env
    body = AgentBuilderTools.__new__(AgentBuilderTools)
    body.tool_registry = reg
    import asyncio

    out = asyncio.run(body.list_available_skills_and_tools())
    assert "tools" not in out
    assert out["catalog_tools"] and "not callable" in out["note"].lower()


def test_a_ticked_tool_named_by_the_question_survives_the_clamp(bind_skills):
    """Live QA: "What is the weather in Boston?" lost get_weather to tools whose descriptions merely
    contain "the" / "what"; ranking ignores filler words and weighs tool-name matches."""
    reg = ScopedToolRegistry()
    noise = {
        "batch_worker_scan": "Scan the batch worker queue and report what is pending.",
        "repo_file_read": "Read the contents of a file in the repository.",
        "wiki_template_read": "Read the template that the wiki uses for what you create.",
        "get_agent_sessions": "List the sessions of an agent and what they did.",
        "system_info": "Report the host name, the CPU and the memory.",
        "wiki_note_search": "Search the wiki for notes that match what is asked.",
        "get_recent_errors": "Return the most recent errors and what caused them.",
    }
    noise["get_weather"] = "Returns current weather for a given location using standard library only."
    for name in sorted(set(noise) | set(REQUIRED_PLATFORM_TOOLS)):
        reg.register_tool(name, noise.get(name, f"{name} tool"), {"type": "object", "properties": {}}, lambda **kw: "ok")
    store = MagicMock()
    store.get_setting.return_value = None
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=reg, state_store=store, telemetry=MagicMock())
    ids = bind_skills({"noise": [n for n in noise if n != "get_weather"], "get-weather": ["get_weather"]})
    agent = _agent("autoreiv", allowed_skill=list(ids))
    for question in ("What is the weather in Boston?", "what's the weather like in Boston right now"):
        names = [t.name for t in kernel._resolve_active_tools(agent, user_content=question)]
        assert len(names) <= MAX_ACTIVE_TOOLS_PER_TURN
        assert "get_weather" in names, (question, names)

