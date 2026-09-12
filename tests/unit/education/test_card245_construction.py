"""CARD-245: Education Construction - generative study artifacts via wiki_note_* only."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.application.education.construction import (
    ARTIFACT_KIND,
    CONSTRUCTION_FORBIDDEN_TOOLS,
    CONSTRUCTION_WIKI_TOOLS,
    assert_construction_tool_allowed,
    build_construction_ask_clause,
    build_study_artifact_markdown,
    construct_study_artifact,
    create_study_artifact_note,
    search_grounding_notes,
)
from src.application.safety.tool_policy_gate import (
    EDUCATION_WIKI_NOTE_TOOLS,
    expand_education_wiki_note_tools,
)
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS, bundled_skill_md


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


def test_build_study_artifact_has_generative_sections():
    body = build_study_artifact_markdown(topic="Standing Jobs", teach_style="bite-size")
    low = body.lower()
    assert "priming schema" in low
    assert "dual coding" in low
    assert "```mermaid" in body
    assert "## Quiz" in body
    assert "## Elaboration" in body
    assert "wiki_note_create" in body
    assert "never wiki_overview" in low
    assert ARTIFACT_KIND in body


def test_construct_lands_inbox_via_wiki_note_create(tmp_path: Path):
    wiki = WikiStore(root_dir=tmp_path / "wiki")
    wiki.scaffold()
    tools = WikiTools(wiki_root=tmp_path / "wiki")
    result = construct_study_artifact(
        topic="Standing Jobs",
        wiki_tools_or_store=tools,
        teach_style="schema + dual + quiz",
        search_first=True,
    )
    assert result["success"] is True
    assert result["inbox"] is True
    path = result["path"].replace("\\", "/")
    assert path.startswith("00_Inbox/")
    assert "wiki_note_create" in result["tools_used"]
    assert "wiki_overview" not in result["tools_used"]
    assert not result["forbidden_called"]
    note = wiki.read_note(path)
    assert note.get("success") is not False
    content = note.get("content") or ""
    assert "Standing Jobs" in content or "standing jobs" in content.lower()
    assert "```mermaid" in content


def test_search_fail_soft_still_creates(tmp_path: Path):
    """Broken search must not abort Construction create [REQ-EDU-CONST-002]."""

    class BrokenSearchStore:
        def search_notes(self, query: str, limit: int = 5):
            raise RuntimeError("search backend down")

        def file_note(self, **kwargs):
            store = WikiStore(root_dir=tmp_path / "wiki2")
            store.scaffold()
            return store.file_note(**kwargs)

    result = construct_study_artifact(
        topic="Fail soft Construction",
        wiki_tools_or_store=BrokenSearchStore(),
        search_first=True,
    )
    assert result["success"] is True
    assert result["inbox"] is True
    search_trace = result["tool_trace"][0]
    assert search_trace.get("skipped") or search_trace.get("error")
    assert "wiki_note_create" in result["tools_used"]


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
    assert "education-construction" in BUNDLED_PACK_IDS
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


def test_search_grounding_notes_empty_query_soft():
    res = search_grounding_notes(None, query="")
    assert res["success"] is True
    assert res.get("skipped") is True
