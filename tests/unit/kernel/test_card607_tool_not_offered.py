"""CARD-607: an agent (Toolsmith) is told plainly which tools it can call.

- The tool_not_offered refusal names a close match and the tools that can be called now (kernel gate and
  registry use the same text).
- The authoring catalog marks each tool with you_can_call for the current caller, so "this tool exists" is
  not read as "call it".
"""

from __future__ import annotations

import asyncio

from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS
from src.application.kernel.reply_rules import short_error
from src.application.kernel.tool_registry import ScopedToolRegistry, tool_not_offered_error
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.domain.gateway.models import ToolCall
from tests.unit.agent_skills.catalog import platform_pack_profile
from tests.unit.kernel.test_card578_tools_all_at_once import _agent, _kernel, _registry_with


def test_refusal_names_a_close_match_and_what_can_be_called():
    text = tool_not_offered_error("list_skills", {"list_user_skills", "skill_view", "propose_skill"})
    assert text.startswith("tool_not_offered:Tool 'list_skills' was not in the tools sent on this call")
    assert "Did you mean list_user_skills?" in text
    assert "Tools you can call now: list_user_skills, propose_skill, skill_view." in text


def test_refusal_lists_at_most_25_and_counts_the_rest():
    names = {f"tool_{i:02d}" for i in range(30)}
    text = tool_not_offered_error("zzz", names)
    assert "tool_24" in text and "tool_25" not in text and "(+5 more)" in text
    assert "Did you mean" not in text


def test_refusal_with_nothing_offered_says_answer_in_text():
    assert tool_not_offered_error("lookup_agents", set()).endswith("No tools are offered on this call; answer in text.")


def test_the_failed_note_still_drops_the_machine_code():
    assert short_error(tool_not_offered_error("x", {"y"})).startswith("Tool 'x' was not in the tools sent")


def test_kernel_gate_and_registry_use_the_same_refusal():
    agent = _agent(allowed_skill=["wiki-knowledge"])
    reg = _registry_with(set(REQUIRED_PLATFORM_TOOLS) | {"wiki_note_read", "wiki_note_search"})
    call = ToolCall(id="c1", name="wiki_note_search", arguments={})
    offered = {"wiki_note_read", "ask_clarification"}
    expected = tool_not_offered_error("wiki_note_search", offered)
    assert "Tools you can call now: ask_clarification, wiki_note_read." in expected
    assert _kernel(reg)._gate_tool_call(call, "s1", agent, offered=offered).error == expected
    assert asyncio.run(reg.execute(call, agent, offered=offered)).error == expected


def _catalog_registry(seen):
    reg = ScopedToolRegistry()
    for name in ("lookup_agents", "list_project_dir", "register_native_tool"):
        reg.register_tool(name, f"{name} tool", {"type": "object", "properties": {}}, lambda **kw: "ok")
    builder = AgentBuilderTools.__new__(AgentBuilderTools)
    builder.tool_registry = reg

    async def catalog(**kwargs):
        seen.append(await builder.list_available_skills_and_tools())
        return "ok"

    reg.register_tool("list_available_skills_and_tools", "catalog", {"type": "object", "properties": {}}, catalog)
    return reg


def test_catalog_marks_only_offered_tools_as_callable():
    seen = []
    reg = _catalog_registry(seen)
    toolsmith = platform_pack_profile("toolsmith")
    call = ToolCall(id="c1", name="list_available_skills_and_tools", arguments={})
    res = asyncio.run(reg.execute(call, toolsmith, offered={"list_available_skills_and_tools", "register_native_tool"}))
    assert res.success, res.error
    rows = {row["name"]: row["you_can_call"] for row in seen[0]["catalog_tools"]}
    assert rows == {
        "lookup_agents": False, "list_project_dir": False, "register_native_tool": True,
        "list_available_skills_and_tools": True,
    }
    assert "you_can_call" in seen[0]["note"]


def test_catalog_outside_a_model_call_has_no_marking():
    seen = []
    reg = _catalog_registry(seen)
    builder = AgentBuilderTools.__new__(AgentBuilderTools)
    builder.tool_registry = reg
    out = asyncio.run(builder.list_available_skills_and_tools())
    assert all("you_can_call" not in row for row in out["catalog_tools"])
