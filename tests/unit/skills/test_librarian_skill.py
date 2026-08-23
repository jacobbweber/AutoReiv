"""
Unit tests for Librarian Skill (YAML Frontmatter & PARA-Wiki) [REQ-AGENTS-005].
"""

import os
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
title: Project AutoReiv Architecture
category: Projects
tags:
  - agentic
  - architecture
status: active
---

# AutoReiv System

This is the system body text.
"""
    parsed = skill.parse_yaml_frontmatter(doc_text)
    assert parsed["frontmatter"]["title"] == "Project AutoReiv Architecture"
    assert parsed["frontmatter"]["category"] == "Projects"
    assert "agentic" in parsed["frontmatter"]["tags"]
    assert "# AutoReiv System" in parsed["body"]


def test_create_and_read_wiki_note(skill, wiki_dir):
    res = skill.create_wiki_note(
        relative_path="projects/autoreiv.md",
        title="AutoReiv Control Plane",
        category="Projects",
        tags=["ai", "control-plane"],
        content="System specs and documentation.",
    )
    assert res["success"] is True
    assert os.path.exists(os.path.join(wiki_dir, "projects", "autoreiv.md"))

    # Read back
    read_res = skill.read_wiki_note("projects/autoreiv.md")
    assert read_res["success"] is True
    assert read_res["title"] == "AutoReiv Control Plane"
    assert "System specs" in read_res["body"]


def test_path_traversal_denial(skill):
    # Attempting to write outside wiki_root
    res = skill.create_wiki_note(
        relative_path="../../sensitive.txt",
        title="Malicious Note",
        category="Inbox",
        content="Secret",
    )
    assert res["success"] is False
    assert "traversal" in res["error"].lower() or "outside" in res["error"].lower()


def test_list_wiki_notes(skill):
    skill.create_wiki_note("projects/p1.md", title="Project 1", category="Projects", content="Body 1")
    skill.create_wiki_note("areas/health.md", title="Health Area", category="Areas", content="Body 2")

    notes = skill.list_wiki_notes()
    assert len(notes) == 2

    project_notes = skill.list_wiki_notes(category="Projects")
    assert len(project_notes) == 1
    assert project_notes[0]["title"] == "Project 1"


@pytest.mark.asyncio
async def test_librarian_registered_tool_execution(skill):
    registry = ScopedToolRegistry()
    skill.register_tools(registry)

    call = ToolCall(
        id="call_lib",
        name="wiki_note_create",
        arguments={
            "relative_path": "inbox/quick_note.md",
            "title": "Quick Thought",
            "category": "Inbox",
            "tags": ["idea"],
            "content": "A sudden realization.",
        },
    )
    res = await registry.execute(call, LIBRARIAN_PROFILE)
    assert res.success is True
    assert res.output["title"] == "Quick Thought"
