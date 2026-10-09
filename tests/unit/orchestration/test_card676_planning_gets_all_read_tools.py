"""CARD-676: a planning (Formulate) step is sent all of the agent's granted read tools, not only the job's match.

Live, a wiki job's Formulate called wiki_template_list (granted, read-only) and was refused because the job's
match had not included it. With CARD-674 labels, planning can safely get every granted read tool; the gate allows
them in Formulate, and Execute is still narrowed to the match.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_access import READ, tool_access
from src.application.orchestration.phase_roles import format_planning_tools_block
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall

MATCH = ["tool.wiki_note_search", "tool.wiki_note_read", "tool.wiki_note_create", "skill.education-wiki-curation"]


@pytest.fixture(scope="module")
def app_state(tmp_path_factory):
    from src.web.app import create_app

    root = tmp_path_factory.mktemp("card676")
    keys = ("AUTOREIV_DATA_DIR", "AUTOREIV_DB_PATH", "AUTOREIV_WIKI_PATH")
    keep = {k: os.environ.get(k) for k in keys}
    os.environ["AUTOREIV_DATA_DIR"] = str(root / "data")
    os.environ["AUTOREIV_DB_PATH"] = str(root / "data" / "database" / "autoreiv.db")
    os.environ["AUTOREIV_WIKI_PATH"] = str(root / "data" / "wiki")
    (root / "data" / "wiki").mkdir(parents=True)
    try:
        app = create_app()
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return app.state


@pytest.fixture(scope="module")
def setup(app_state):
    registry = app_state.tool_registry
    agent = app_state.registry.get_agent("autoreiv")
    store = MagicMock()
    store.get_setting.return_value = None
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=registry, state_store=store, telemetry=MagicMock())
    granted = {t.name for t in registry.get_tools_for_agent(agent)}
    return kernel, agent, granted


def test_planning_step_gets_every_granted_read_tool(setup):
    kernel, agent, granted = setup
    sent = {t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=MATCH, planning_phase=True)}
    granted_reads = {n for n in granted if tool_access(n) == READ}
    assert "wiki_template_list" in granted_reads  # the tool refused live
    assert sent == granted_reads


def test_execute_step_is_still_narrowed_to_the_match(setup):
    kernel, agent, _ = setup
    sent = {t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=MATCH, planning_phase=False)}
    assert "wiki_note_create" in sent
    assert "wiki_template_list" not in sent


def test_gate_allows_a_granted_read_tool_outside_the_match_while_planning(setup):
    _, agent, _ = setup
    gate = ToolPolicyGate(None)
    call = ToolCall(id="c1", name="wiki_template_list", arguments={})
    planning = gate.evaluate(call, agent, matched_capability_ids=MATCH, planning_phase=True)
    assert planning.verdict != ToolPolicyVerdict.BLOCK, planning.reason
    executing = gate.evaluate(call, agent, matched_capability_ids=MATCH, planning_phase=False)
    assert executing.verdict == ToolPolicyVerdict.BLOCK  # Execute keeps the job's match


def test_gate_still_refuses_writes_while_planning_even_when_matched(setup):
    _, agent, _ = setup
    d = ToolPolicyGate(None).evaluate(ToolCall(id="c2", name="wiki_note_create", arguments={}), agent,
                                      matched_capability_ids=MATCH, planning_phase=True)
    assert d.verdict == ToolPolicyVerdict.BLOCK and d.policy_source == "planning_phase"


def test_tools_block_lists_the_granted_reads_as_callable(setup):
    kernel, agent, _ = setup
    sent = [t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=MATCH, planning_phase=True)]
    block = format_planning_tools_block(sent, MATCH, granted=set(sent))
    assert "wiki_template_list" in block.splitlines()[0]
