"""CARD-674: every platform tool is labeled read or write, and a planning (Formulate) step is sent only read tools.

Before: the plan-only rule blocked handoff, the hitl high-risk list and tools with a declared high risk. No tool
declared a risk, so wiki_template_create, wiki_template_update, wiki_note_archive and other writes reached the
planner. Now planning is allow-listed by label: read tools only; a write or unlabeled tool is not used while planning.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.kernel.tool_access import READ, WRITE, READ_TOOLS, WRITE_TOOLS, tool_access
from src.application.orchestration.phase_roles import planning_phase_block_reason
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall

LIVE_WRITES_SEEN_IN_FORMULATE = ["wiki_template_create", "wiki_template_update", "wiki_note_archive"]
OTHER_WRITES = ["promote_artifact_to_wiki", "memorize_fact", "wiki_note_create", "wiki_note_update",
                "wiki_note_append", "wiki_note_organize", "propose_followup", "write_card", "cli_exec"]
PLANNER_READS = ["wiki_note_search", "wiki_note_read", "wiki_note_list", "wiki_overview", "wiki_template_list",
                 "wiki_template_read", "recall_agent_memory", "repo_file_read", "list_available_skills_and_tools"]


@pytest.fixture(scope="module")
def app_registry(tmp_path_factory):
    import os

    from src.web.app import create_app

    root = tmp_path_factory.mktemp("card674")
    keep = {k: os.environ.get(k) for k in ("AUTOREIV_DATA_DIR", "AUTOREIV_DB_PATH", "AUTOREIV_WIKI_PATH")}
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
    return app.state.tool_registry, app.state


def test_labels_are_read_or_write_and_never_both():
    assert not (READ_TOOLS & WRITE_TOOLS)
    assert tool_access("wiki_note_search") == READ
    assert tool_access("wiki_template_create") == WRITE
    assert tool_access("no_such_tool") is None


def test_every_platform_tool_the_app_registers_is_labeled(app_registry):
    registry, _ = app_registry
    builtin = registry.builtin_tool_names()
    assert len(builtin) > 80
    unlabeled = sorted(n for n in builtin if tool_access(n) is None)
    assert unlabeled == [], f"label these read or write in src/application/kernel/tool_access.py: {unlabeled}"


def test_no_stale_labels(app_registry):
    registry, _ = app_registry
    stale = sorted((READ_TOOLS | WRITE_TOOLS) - registry.builtin_tool_names())
    assert stale == [], f"labels for tools that are not registered: {stale}"


@pytest.mark.parametrize("name", LIVE_WRITES_SEEN_IN_FORMULATE + OTHER_WRITES + ["handoff_to_agent"])
def test_write_tools_are_not_used_while_planning(name):
    assert planning_phase_block_reason(name) is not None


@pytest.mark.parametrize("name", PLANNER_READS)
def test_read_tools_are_used_while_planning(name):
    assert planning_phase_block_reason(name) is None


def test_an_unlabeled_tool_is_not_used_while_planning():
    why = planning_phase_block_reason("mcp_someserver_do_thing")
    assert why and "read or write" in why


def test_a_declared_read_only_risk_counts_as_read():
    assert planning_phase_block_reason("mcp_someserver_lookup", "read_only") is None
    assert planning_phase_block_reason("wiki_note_search", "write") is not None


def _shipped_autoreiv(state):
    return state.registry.get_agent("autoreiv")


def test_the_gate_refuses_a_write_tool_in_formulate_and_allows_a_read(app_registry):
    _, state = app_registry
    agent = _shipped_autoreiv(state)
    gate = ToolPolicyGate(None)
    write = gate.evaluate(ToolCall(id="c1", name="wiki_template_create", arguments={}), agent, planning_phase=True)
    assert write.verdict == ToolPolicyVerdict.BLOCK and write.policy_source == "planning_phase"
    read = gate.evaluate(ToolCall(id="c2", name="wiki_note_search", arguments={}), agent, planning_phase=True)
    assert read.verdict != ToolPolicyVerdict.BLOCK


def test_shipped_autoreiv_formulate_step_is_sent_only_read_tools(app_registry):
    from src.application.kernel.agent_kernel import AgentKernel

    registry, state = app_registry
    agent = _shipped_autoreiv(state)
    store = MagicMock()
    store.get_setting.return_value = None
    kernel = AgentKernel(gateway=MagicMock(), tool_registry=registry, state_store=store, telemetry=MagicMock())
    granted = {t.name for t in registry.get_tools_for_agent(agent)}
    assert set(LIVE_WRITES_SEEN_IN_FORMULATE) <= granted  # the shipped profile really is granted them
    sent = {t.name for t in kernel._resolve_active_tools(agent, matched_capability_ids=None, planning_phase=True)}
    assert sent, "a planning step still gets its read tools"
    assert {n for n in sent if tool_access(n) != READ} == set()
    assert not (set(LIVE_WRITES_SEEN_IN_FORMULATE) & sent)
