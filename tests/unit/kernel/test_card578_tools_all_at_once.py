"""CARD-578 (ADR-0064): tools load all at once.

Guards: every tool of the agent's ticked skills plus the base tools is sent on every model call, whatever
the question; skill_view / list_user_skills are sent when the agent has skills; activate_skill is gone;
a tool that was not in the tools sent on that call is refused (kernel gate and registry); a bare name no
longer resolves to an mcp_* tool.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import src.application.kernel.agent_kernel as kernel_mod
from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety.tool_policy_gate import ToolPolicyGate
from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile
from tests.unit.agent_skills.catalog import platform_pack_profile

QUESTIONS = ("hi", "", "What is the weather in Boston?", "read src/app.py and patch the typo", "search my wiki")


def _registry_with(names) -> ScopedToolRegistry:
    reg = ScopedToolRegistry()
    for name in sorted(names):
        reg.register_tool(name, f"{name} tool", {"type": "object", "properties": {}}, lambda **kw: "ok")
    return reg


def _kernel(reg) -> AgentKernel:
    store = MagicMock()
    store.get_setting.return_value = None
    return AgentKernel(gateway=MagicMock(), tool_registry=reg, state_store=store, telemetry=MagicMock(),
                       tool_policy_gate=ToolPolicyGate(store))


def _agent(agent_id="c578", **kw) -> AgentProfile:
    return AgentProfile(id=agent_id, name="A", description="d", system_prompt="p", **kw)


def test_the_cap_ranking_and_activation_are_gone():
    assert not hasattr(kernel_mod, "MAX_ACTIVE_TOOLS_PER_TURN")
    assert not hasattr(AgentKernel, "_match_intent_skills")
    assert "activate_skill" not in REQUIRED_PLATFORM_TOOLS
    with pytest.raises(ImportError):
        __import__("src.application.kernel.tool_ranker")


@pytest.mark.parametrize("agent_id", ["developer", "autoreiv", "architect", "tutor", "toolsmith"])
def test_every_ticked_tool_is_sent_on_every_call(agent_id):
    agent = platform_pack_profile(agent_id)
    allowed = resolve_allowed_tools(agent)
    kernel = _kernel(_registry_with(allowed.names))
    for question in QUESTIONS:
        sent = {t.name for t in kernel._resolve_active_tools(agent, user_content=question)}
        assert sent == set(allowed.names), (agent_id, question, set(allowed.names) ^ sent)
    assert {"skill_view", "list_user_skills"} <= sent  # the skill index works for every agent with skills
    assert "activate_skill" not in sent


def test_developer_turn_one_gets_its_full_set():
    dev = platform_pack_profile("developer")
    names = resolve_allowed_tools(dev).names
    sent = [t.name for t in _kernel(_registry_with(names))._resolve_active_tools(dev, user_content="hi")]
    assert len(sent) == len(names) == 27, sorted(sent)  # CARD-633: +run_journey (was 26 after CARD-632)
    for tool in ("read_project_file", "patch_project_file", "search_project", "run_project_checks", "skill_view",
                 "list_journey_reports", "read_journey_report", "summarize_journey_failures", "run_journey"):
        assert tool in sent


def test_skill_view_is_sent_only_when_the_agent_has_skills():
    reg = _registry_with(set(REQUIRED_PLATFORM_TOOLS) | {"skill_view", "list_user_skills", "wiki_note_read"})
    kernel = _kernel(reg)
    bare = {t.name for t in kernel._resolve_active_tools(_agent(), user_content="hi")}
    assert "skill_view" not in bare and "list_user_skills" not in bare
    ticked = {t.name for t in kernel._resolve_active_tools(_agent(allowed_skill=["wiki-knowledge"]), user_content="hi")}
    assert {"skill_view", "list_user_skills", "wiki_note_read"} <= ticked


def test_kernel_gate_refuses_a_tool_that_was_not_sent_on_this_call():
    agent = _agent(allowed_skill=["wiki-knowledge"])
    reg = _registry_with(set(REQUIRED_PLATFORM_TOOLS) | {"wiki_note_read", "wiki_note_search"})
    kernel = _kernel(reg)
    call = ToolCall(id="c1", name="wiki_note_search", arguments={})
    refused = kernel._gate_tool_call(call, "s1", agent, offered={"wiki_note_read"})
    assert refused is not None and refused.success is False
    assert (refused.error or "").startswith("tool_not_offered:"), refused.error
    assert kernel._gate_tool_call(call, "s1", agent, offered={"wiki_note_read", "wiki_note_search"}) is None


async def test_registry_refuses_a_tool_that_was_not_sent_on_this_call():
    agent = _agent(allowed_skill=["wiki-knowledge"])
    reg = _registry_with(set(REQUIRED_PLATFORM_TOOLS) | {"wiki_note_read", "wiki_note_search"})
    call = ToolCall(id="c1", name="wiki_note_search", arguments={})
    refused = await reg.execute(call, agent, offered={"wiki_note_read"})
    assert refused.success is False and (refused.error or "").startswith("tool_not_offered:")
    assert (await reg.execute(call, agent, offered={"wiki_note_search"})).success is True
    assert (await reg.execute(call, agent)).success is True  # platform-side run (HITL resume): allowed set only


async def test_an_unticked_tool_is_refused_even_if_offered():
    agent = _agent(allowed_skill=["wiki-knowledge"])
    reg = _registry_with(set(REQUIRED_PLATFORM_TOOLS) | {"wiki_note_read", "execute_code"})
    res = await reg.execute(ToolCall(id="c1", name="execute_code", arguments={}), agent, offered={"execute_code"})
    assert res.success is False and "not authorized" in (res.error or "")


async def test_a_bare_name_no_longer_resolves_to_an_mcp_tool(bind_skills):
    reg = ScopedToolRegistry()
    reg.mount_mcp_tool(
        name="mcp_srv_lookup",
        definition=ToolDefinition(name="mcp_srv_lookup", description="Lookup", parameters={"type": "object"}),
        handler=lambda **kw: "ok",
    )
    reg.register_tool("lookup_plain", "plain", {"type": "object", "properties": {}}, lambda **kw: "ok")
    agent = _agent(allowed_skill=bind_skills({"mcp-srv": ["mcp_srv_*"]}))
    bare = await reg.execute(ToolCall(id="c1", name="lookup", arguments={}), agent)
    assert bare.success is False
    scoped = await reg.execute(ToolCall(id="c2", name="mcp_srv_lookup", arguments={}), agent, offered={"mcp_srv_lookup"})
    assert scoped.success is True, scoped.error
    other = _agent(allowed_skill=bind_skills({"plain": ["lookup"]}))
    reverse = await reg.execute(ToolCall(id="c3", name="mcp_srv_lookup", arguments={}), other)
    assert reverse.success is False
