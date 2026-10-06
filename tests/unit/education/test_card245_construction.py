"""CARD-245: Education Construction - wiki_note_* only (the template generator was removed in CARD-648)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.application.education.construction import (
    CONSTRUCTION_FORBIDDEN_TOOLS,
    CONSTRUCTION_WIKI_TOOLS,
    assert_construction_tool_allowed,
    build_construction_ask_clause,
    create_study_artifact_note,
)
from src.application.safety.tool_policy_gate import (
    EDUCATION_WIKI_NOTE_TOOLS,
    expand_education_wiki_note_tools,
)
from src.application.skills.wiki_tools import WikiTools
from tests.unit.agent_skills.catalog import BUNDLED_SKILL_IDS, bundled_skill_md


def test_construction_allowlist_matches_card241():
    assert CONSTRUCTION_WIKI_TOOLS == set(EDUCATION_WIKI_NOTE_TOOLS)
    assert "wiki_note_create" in CONSTRUCTION_WIKI_TOOLS
    assert "wiki_overview" in CONSTRUCTION_FORBIDDEN_TOOLS
    assert "wiki_graph" in CONSTRUCTION_FORBIDDEN_TOOLS


def test_assert_forbids_wiki_overview():
    with pytest.raises(ValueError, match="wiki_overview"):
        assert_construction_tool_allowed("wiki_overview")
    assert_construction_tool_allowed("wiki_note_create")
    assert_construction_tool_allowed("wiki_note_search")


def test_create_rejects_if_overview_slipped_in(tmp_path: Path):
    tools = WikiTools(wiki_root=tmp_path / "wiki3")
    with pytest.raises(ValueError, match="wiki_overview"):
        assert_construction_tool_allowed("wiki_overview")
    res = create_study_artifact_note(
        tools,
        title="Guard note",
        content="# hi\n",
        topic="guard",
    )
    assert res["tool"] == "wiki_note_create"
    assert res["success"] is True


def test_construction_module_never_calls_wiki_overview():
    import src.application.education.construction as mod

    src = inspect.getsource(mod)
    assert "get_wiki_overview" not in src
    assert "wiki_overview(" not in src
    assert "never" in src.lower() and "wiki_overview" in src


def test_education_construction_skill_seed_bundled():
    assert "education-construction" in BUNDLED_SKILL_IDS
    body = bundled_skill_md("education-construction").read_text(encoding="utf-8")
    tools_section = body.split("## Order")[0]
    allow_part = tools_section.split("Forbidden")[0]
    assert "wiki_note_create" in allow_part
    assert "`wiki_overview`" not in allow_part
    assert "Forbidden" in body
    assert "wiki_overview" in body.split("Forbidden", 1)[1]


def test_construction_skill_expands_wiki_note_allowlist():
    expanded = expand_education_wiki_note_tools(["skill.education-construction"])
    assert expanded == set(EDUCATION_WIKI_NOTE_TOOLS)
    assert "wiki_overview" not in expanded


def test_build_construction_ask_clause_shapes_mode():
    clause = build_construction_ask_clause(topic="Jobs", teach_style="bite-size")
    assert "Mode: Construction" in clause
    assert "education-construction" in clause
    assert "wiki_note_create" in clause
    assert "never wiki_overview" in clause
    assert "00_Inbox" in clause
