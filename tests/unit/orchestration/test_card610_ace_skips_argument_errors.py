"""CARD-610: online ACE learns only from real tool failures.

A refused call that ran nothing and already told the model the fix (unknown or missing arguments, a tool not
offered on this call, a tool the agent may not use, an unknown tool name) is not a lesson: it drafts no
"Append ACE insight" approval and adds no "Note: ... failed" line. A real failure still drafts one.
"""

from __future__ import annotations

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.reply_rules import counts_as_failure
from src.application.kernel.tool_registry import (
    argument_mismatch_error,
    is_self_correcting_refusal,
    tool_not_offered_error,
)
from src.application.orchestration.ace_online import is_ace_lesson_error, record_failed_turn_delta, reflect_failed_turn
from src.application.skills.user_catalog import UserSkillCatalog
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _wiki_note_list(category=None, domain=None, topic=None, status=None, tag=None):
    return []


ARG_REFUSAL = argument_mismatch_error(
    "wiki_note_list", _wiki_note_list, {"properties": {"tag": {"type": "string"}}}, {"limit": 5}
)
REFUSALS = [
    ARG_REFUSAL,
    tool_not_offered_error("wiki_overview", {"wiki_note_list", "wiki_note_search"}),
    "Tool 'execute_code' is not authorized for agent 'c610'.",
    "Tool 'wiki_lookup' not found in system registry.",
]
REAL_FAILURES = ["Timed out after 30s", "Note not found: gardening.md", "Tool execution error"]


@pytest.fixture
def env(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "state.db")
    store.initialize_db()
    data_dir = tmp_path / "data"
    catalog = UserSkillCatalog(skills_dir=data_dir / "skills")
    catalog.save_skill("c610-notes", "c610-notes", "Notes SOP.", "Search, then read.")  # not a platform id: save_skill would write the repo pack
    return {"store": store, "data_dir": data_dir, "catalog": catalog}


def _record(env, errors, error_message=None):
    return record_failed_turn_delta(
        env["store"], skill_id="c610-notes", data_dir=env["data_dir"], session_id="s610", agent_id="c610",
        tool_errors=errors, error_message=error_message, catalog=env["catalog"],
    )


def test_the_argument_refusal_text_is_the_one_the_filter_knows():
    assert ARG_REFUSAL and "Unknown: limit." in ARG_REFUSAL


@pytest.mark.parametrize("error", REFUSALS)
def test_refusals_are_not_lessons_or_failures(error):
    assert is_self_correcting_refusal(error)
    assert not is_ace_lesson_error(error)
    assert not counts_as_failure("wiki_note_list", False, error)


@pytest.mark.parametrize("error", REAL_FAILURES)
def test_real_failures_are_still_lessons(error):
    assert not is_self_correcting_refusal(error)
    assert is_ace_lesson_error(error)
    assert counts_as_failure("wiki_note_list", False, error)


def test_approval_parks_and_empty_errors_stay_out():
    assert not is_ace_lesson_error("approval_required:appr_1")
    assert is_ace_lesson_error("")  # the kernel records an empty error as "Tool execution error"


@pytest.mark.parametrize("error", REFUSALS)
def test_a_refusal_drafts_no_approval(env, error):
    result = _record(env, [{"tool_name": "wiki_note_list", "error": error}])
    assert result["deltas"] == 0 and result["status"] is None
    assert env["store"].get_pending_approvals(session_id="s610") == []
    assert "Tool error" not in reflect_failed_turn(skill_id="c610-notes", tool_errors=[{"tool_name": "x", "error": error}])["insight"]


def test_a_real_failure_still_drafts_one(env):
    result = _record(env, [
        {"tool_name": "wiki_note_list", "error": ARG_REFUSAL},
        {"tool_name": "wiki_note_read", "error": "Timed out after 30s"},
    ])
    assert result["deltas"] == 1, result
    pending = env["store"].get_pending_approvals(session_id="s610")
    assert len(pending) == 1
    payload = str(pending[0])
    assert "Timed out" in payload and "limit" not in payload


def test_kernel_does_not_collect_refusals():
    kernel = AgentKernel.__new__(AgentKernel)
    kernel._ace_tool_errors = []
    for error in REFUSALS + ["approval_required:appr_1"]:
        kernel._ace_note_tool("wiki_note_list", False, error)
    assert kernel._ace_tool_errors == []
    kernel._ace_note_tool("wiki_note_read", False, "Timed out after 30s")
    assert [e["error"] for e in kernel._ace_tool_errors] == ["Timed out after 30s"]


def test_wiki_list_and_search_descriptions_say_which_takes_a_limit(tmp_path):
    from src.application.kernel.tool_registry import ScopedToolRegistry
    from src.application.skills.wiki_tools import WikiTools

    reg = ScopedToolRegistry()
    WikiTools(wiki_root=tmp_path).register_tools(reg)
    defs = {d.name: d for d in reg.list_tools()}
    listing, search = defs["wiki_note_list"], defs["wiki_note_search"]
    assert "limit" not in listing.parameters["properties"]  # no parameter added just to absorb the guess
    assert "no query or limit parameter" in listing.description and "wiki_note_search" in listing.description
    assert "limit" in search.parameters["properties"] and "tags is a list" in search.description
