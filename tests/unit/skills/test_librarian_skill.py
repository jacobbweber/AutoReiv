"""
Unit tests for Librarian Skill (YAML Frontmatter & Wiki Management) [REQ-AGENTS-005, REQ-WIKI-005].
"""

import tempfile

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.librarian_skill import LibrarianSkill
from src.domain.agents.profiles import LIBRARIAN_PROFILE
from src.domain.gateway.models import ToolCall


@pytest.fixture
def wiki_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def skill(wiki_dir):
    return LibrarianSkill(wiki_root=wiki_dir)


def test_parse_yaml_frontmatter(skill):
    doc_text = """---
uid: "20260823-120000"
title: "Project AutoReiv Architecture"
domain: "information_technology"
topic: "ai_engineering"
tags:
  - agentic
  - architecture
status: "final"
---

# AutoReiv System

This is the system body text.
"""
    parsed = skill.parse_yaml_frontmatter(doc_text)
    assert parsed["frontmatter"]["title"] == "Project AutoReiv Architecture"
    assert parsed["frontmatter"]["domain"] == "information_technology"
    assert "agentic" in parsed["frontmatter"]["tags"]
    assert "# AutoReiv System" in parsed["body"]


def test_create_and_read_wiki_note(skill, wiki_dir):
    res = skill.create_wiki_note(
        title="AutoReiv Control Plane",
        domain="information_technology",
        topic="ai_engineering",
        tags=["ai", "control-plane"],
        content="System specs and documentation.",
    )
    assert res["success"] is True
    rel_path = res["path"]

    # Read back
    read_res = skill.read_wiki_note(rel_path)
    assert read_res["success"] is True
    assert read_res["title"] == "AutoReiv Control Plane"
    assert "System specs" in read_res["body"]


def test_path_traversal_denial(skill):
    # Attempting to write outside wiki_root
    res = skill.create_wiki_note(
        relative_path="../../sensitive.txt",
        title="Malicious Note",
        content="Secret",
    )
    assert res["success"] is False
    assert "traversal" in res["error"].lower() or "outside" in res["error"].lower()


def test_update_and_search_wiki_notes(skill):
    res = skill.create_wiki_note(
        title="Kernel Dispatcher",
        domain="information_technology",
        topic="ai_engineering",
        content="Initial content.",
    )
    rel_path = res["path"]

    # Update note
    upd = skill.update_wiki_note(rel_path, content="Updated content with reactive dispatcher.")
    assert upd["success"] is True

    # Search
    hits = skill.search_wiki_notes("reactive")
    assert len(hits) >= 1
    assert "Kernel Dispatcher" in hits[0]["title"]


def test_overview_and_graph(skill):
    skill.create_wiki_note(
        title="Agent Alpha",
        domain="information_technology",
        topic="ai_engineering",
        content="See [[Agent Beta]].",
    )
    skill.create_wiki_note(
        title="Agent Beta",
        domain="information_technology",
        topic="ai_engineering",
        content="Collaborator note.",
    )

    overview = skill.get_wiki_overview()
    assert "Agent Alpha" in overview
    assert "Agent Beta" in overview

    graph = skill.get_wiki_graph()
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1


@pytest.mark.asyncio
async def test_librarian_registered_tool_execution(skill):
    registry = ScopedToolRegistry()
    skill.register_tools(registry)

    call = ToolCall(
        id="call_lib",
        name="wiki_note_create",
        arguments={
            "title": "Quick Thought",
            "category": "inbox",
            "inbox_priority": "need_to_do",
            "tags": ["idea"],
            "content": "A sudden realization.",
        },
    )
    res = await registry.execute(call, LIBRARIAN_PROFILE)
    assert res.success is True
    assert res.output["title"] == "Quick Thought"


def test_organize_wiki_note_from_inbox(skill):
    # 1. Create a note staged in inbox
    inbox_res = skill.create_wiki_note(
        title="Raw Chat Export",
        category="inbox",
        content="Important architectural notes about AutoReiv.",
        relative_path="inbox/raw_chat_export.md",
    )
    assert inbox_res["success"] is True

    # 2. Organize note to permanent taxonomy
    org_res = skill.organize_wiki_note(
        source_path="inbox/raw_chat_export.md",
        target_domain="information_technology",
        target_topic="ai_engineering",
        document_type="atomic_note",
        summary="Architectural findings on AutoReiv control plane.",
        tags=["autoreiv", "architecture"],
        new_title="AutoReiv Control Plane Architecture",
    )
    assert org_res["success"] is True
    assert org_res["target_path"] == "notes/information_technology/ai_engineering/raw_chat_export.md"
    assert org_res["domain"] == "information_technology"
    assert org_res["topic"] == "ai_engineering"

    # 3. Read back from new location
    read_back = skill.read_wiki_note("notes/information_technology/ai_engineering/raw_chat_export.md")
    assert read_back["success"] is True
    assert read_back["frontmatter"]["title"] == "AutoReiv Control Plane Architecture"
    assert read_back["frontmatter"]["domain"] == "information_technology"
    assert read_back["frontmatter"]["topic"] == "ai_engineering"
    assert read_back["frontmatter"]["summary"] == "Architectural findings on AutoReiv control plane."
    assert "autoreiv" in read_back["frontmatter"]["tags"]

    # 4. Confirm source is removed from inbox
    old_read = skill.read_wiki_note("inbox/raw_chat_export.md")
    assert old_read["success"] is False
