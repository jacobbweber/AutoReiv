"""CARD-241 Education Wiki allowlist + fail-soft unknown/out-of-subset tools."""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

import pytest

from src.application.safety.tool_policy_gate import (
    EDUCATION_WIKI_NOTE_TOOLS,
    ToolPolicyGate,
    ToolPolicyVerdict,
    _capability_tool_names,
    expand_education_wiki_note_tools,
)
from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.infrastructure.skills.seed import bundled_skill_md


@pytest.fixture
def store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    s = SQLiteStateStore(db_path=path)
    yield s
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def gate(store):
    return ToolPolicyGate(store=store)


def _agent(**kwargs):
    base = dict(
        id="assistant",
        allowed_tool_names=[
            "wiki_note_search",
            "wiki_note_read",
            "wiki_note_list",
            "wiki_note_create",
            "wiki_overview",
            "wiki_graph",
        ],
        storage_enabled=False,
        mcp_servers=[],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_education_skills_forbid_wiki_overview():
    priming = bundled_skill_md("education-priming").read_text(encoding="utf-8")
    dual = bundled_skill_md("education-dual-coding").read_text(encoding="utf-8")
    for body in (priming, dual):
        assert "wiki_overview" not in body.split("Forbidden")[0] or "never" in body.lower()
        assert "wiki_note_create" in body
        assert "wiki_note_search" in body or "wiki_note_list" in body
        # Must explicitly forbid bare overview (CARD-241 AC).
        assert "wiki_overview" in body
        assert "Forbidden" in body or "never" in body.lower()
        # Forbidden section should ban calling it; Tools order must not recommend it as a step.
        tools_section = body.split("## Order")[0]
        assert "`wiki_overview`" not in tools_section.split("Forbidden")[0]


def test_education_skill_match_expands_wiki_note_only():
    expanded = expand_education_wiki_note_tools(["skill.education-priming"])
    assert expanded == set(EDUCATION_WIKI_NOTE_TOOLS)
    assert "wiki_overview" not in expanded
    subset = _capability_tool_names(["skill.education-priming"])
    assert subset is not None
    assert "wiki_note_create" in subset
    assert "wiki_overview" not in subset


def test_skill_only_non_education_does_not_poison_subset():
    # Non-education skill-only match must not yield empty subset that blocks everything.
    assert _capability_tool_names(["skill.some-other-pack"]) is None


def test_wiki_overview_out_of_subset_fail_soft(gate):
    """wiki_overview BLOCK (capability_subset) fails soft / skip - does not abort Job [CARD-241]."""
    d = gate.evaluate(
        ToolCall(id="c1", name="wiki_overview", arguments={}),
        _agent(),
        matched_capability_ids=["skill.education-priming"],
        registry_tool_names={
            "wiki_note_search",
            "wiki_note_create",
            "wiki_overview",
            "wiki_note_read",
            "wiki_note_list",
        },
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert d.policy_source == "capability_subset"

    result = gate.apply_to_tool_result(
        d,
        ToolCall(id="c1", name="wiki_overview", arguments={}),
        session_id="sess_edu",
        agent=_agent(),
        hitl_engine=None,
        approval_mode="ask",
        job_id="job_test",
        log=False,
    )
    assert result is not None
    assert result.success is True
    assert isinstance(result.output, dict)
    assert result.output.get("skipped") is True
    assert result.output.get("fail_soft") is True
    assert result.error is None


def test_unknown_registry_tool_fail_soft(gate):
    d = gate.evaluate(
        ToolCall(id="c2", name="totally_ghost_tool", arguments={}),
        _agent(allowed_tool_names=["totally_ghost_tool", "wiki_note_create"]),
        registry_tool_names={"wiki_note_create"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert d.policy_source == "registry"
    result = gate.apply_to_tool_result(
        d,
        ToolCall(id="c2", name="totally_ghost_tool", arguments={}),
        session_id="sess_unk",
        agent=_agent(allowed_tool_names=["totally_ghost_tool", "wiki_note_create"]),
        hitl_engine=None,
        log=False,
    )
    assert result.success is True
    assert result.output.get("fail_soft") is True


def test_explicit_block_tools_still_hard_fail(gate, store):
    store.set_setting(
        "tool_policy",
        {"block_tools": ["wiki_note_search"], "require_confirm_tools": [], "safe_tools": []},
    )
    gate.reload_policy()
    d = gate.evaluate(
        ToolCall(id="c3", name="wiki_note_search", arguments={}),
        _agent(),
        registry_tool_names={"wiki_note_search", "wiki_note_create"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert d.policy_source == "settings.block_tools"
    result = gate.apply_to_tool_result(
        d,
        ToolCall(id="c3", name="wiki_note_search", arguments={}),
        session_id="sess_hard",
        agent=_agent(),
        hitl_engine=None,
        log=False,
    )
    assert result.success is False
    assert "tool_policy_blocked" in str(result.error)


def test_education_matched_allows_wiki_note_create(gate):
    d = gate.evaluate(
        ToolCall(id="c4", name="wiki_note_create", arguments={"title": "t", "content": "c"}),
        _agent(),
        matched_capability_ids=["skill.education-priming"],
        registry_tool_names={"wiki_note_create", "wiki_note_search", "wiki_overview"},
    )
    # create is high-risk -> REQUIRE_CONFIRM, not BLOCK for subset
    assert d.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
