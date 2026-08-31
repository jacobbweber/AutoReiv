"""
Unit tests for WikiStore Core Engine [REQ-WIKI-001, REQ-WIKI-003, REQ-WIKI-004].
"""

import tempfile

import pytest

from src.domain.wiki.store import WikiStore


@pytest.fixture
def temp_wiki():
    with tempfile.TemporaryDirectory() as tmp:
        store = WikiStore(root_dir=tmp)
        store.scaffold()
        yield store


def test_scaffold_creates_directories(temp_wiki):
    """Verify scaffold creates inbox, notes, and resources folders [REQ-WIKI-001, REQ-WIKI-007]."""
    root = temp_wiki.root_dir
    assert (root / "inbox").exists()
    assert (root / "notes").exists()
    assert (root / "resources" / "operating_manuals").exists()
    assert (root / "resources" / "templates").exists()


def test_file_note_inbox_flat(temp_wiki):
    """Verify filing note into inbox creates flat inbox/<slug>.md note [REQ-WIKI-007]."""
    res = temp_wiki.file_note(
        title="Quick Brainstorm",
        content="Idea for auto-routing...",
        category="inbox",
    )
    assert res["success"] is True
    assert res["path"] == "inbox/quick_brainstorm.md"
    assert (temp_wiki.root_dir / "inbox" / "quick_brainstorm.md").exists()

    tree = temp_wiki.get_tree()
    assert len(tree["inbox"]) == 1
    assert tree["inbox"][0]["title"] == "Quick Brainstorm"


def test_file_and_read_note(temp_wiki):
    """Verify filing and reading notes with frontmatter [REQ-WIKI-001, REQ-WIKI-002]."""
    res = temp_wiki.file_note(
        title="Agentic RAG Patterns",
        content="## Core Concepts\nRetrieval augmented generation...",
        domain="information_technology",
        topic="ai_engineering",
        tags=["rag", "llm"],
        summary="A guide to RAG architectures.",
    )
    assert res["success"] is True
    rel_path = res["path"]
    assert "information_technology" in rel_path
    assert "ai_engineering" in rel_path
    assert rel_path.endswith(".md")

    # Read note back
    read_res = temp_wiki.read_note(rel_path)
    assert read_res["success"] is True
    assert read_res["meta"]["title"] == "Agentic RAG Patterns"
    assert read_res["meta"]["domain"] == "information_technology"
    assert read_res["meta"]["topic"] == "ai_engineering"
    assert "Retrieval augmented generation" in read_res["content"]


def test_non_destructive_write(temp_wiki):
    """Verify writing updates body and timestamps without destroying frontmatter [REQ-WIKI-003]."""
    res = temp_wiki.file_note(
        title="Lucy Architecture",
        content="Version 1",
        domain="information_technology",
        topic="sdlc",
        tags=["architecture", "custom_tag"],
    )
    rel_path = res["path"]

    # Read original
    orig = temp_wiki.read_note(rel_path)
    orig_uid = orig["meta"]["uid"]
    orig_tags = orig["meta"]["tags"]

    # Write new body
    update_res = temp_wiki.write_note(rel_path, content="Version 2 with expanded content.")
    assert update_res["success"] is True

    # Read back
    updated = temp_wiki.read_note(rel_path)
    assert updated["meta"]["uid"] == orig_uid
    assert updated["meta"]["tags"] == orig_tags
    assert updated["content"] == "Version 2 with expanded content."
    assert updated["meta"]["word_count"] == 5


def test_search_notes(temp_wiki):
    """Verify search ranks title matches and body overlap [REQ-WIKI-001]."""
    temp_wiki.file_note(
        title="Docker Containerization Guide",
        content="Using alpine linux containers for microservices.",
        domain="information_technology",
        topic="devops",
    )
    temp_wiki.file_note(
        title="Ansible Action Plugins",
        content="Developing custom action plugins in Python.",
        domain="information_technology",
        topic="ansible",
    )

    hits = temp_wiki.search_notes("docker")
    assert len(hits) >= 1
    assert "Docker" in hits[0]["title"]


def test_graph_wikilinks_extraction(temp_wiki):
    """Verify [[wikilink]] extraction constructs network graph [REQ-WIKI-004]."""
    temp_wiki.file_note(
        title="Core Kernel",
        content="See [[Agent Memory]] and [[Tool Dispatcher]] for details.",
        domain="information_technology",
        topic="ai_engineering",
    )
    temp_wiki.file_note(
        title="Agent Memory",
        content="Episodic and working memory implementations.",
        domain="information_technology",
        topic="ai_engineering",
    )

    graph = temp_wiki.get_graph()
    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1
    assert any(e["target_title"] == "Agent Memory" or "agent_memory" in e["target"] for e in graph["edges"])


def test_overview_prompt_summary(temp_wiki):
    """Verify get_overview returns compact text under token limit [REQ-WIKI-001]."""
    temp_wiki.file_note(
        title="Kernel Architecture",
        content="Specs...",
        domain="information_technology",
        topic="ai_engineering",
    )
    overview = temp_wiki.get_overview()
    assert "information_technology" in overview
    assert "Kernel Architecture" in overview
    assert len(overview.split()) < 150


def test_append_note_safely(temp_wiki):
    """Verify append_note safely appends markdown, updates word count and hash [CARD-125]."""
    res = temp_wiki.file_note(
        title="Daily Standup",
        content="Morning check-in complete.",
        domain="operations",
        topic="worklog",
        tags=["standup"],
    )
    rel_path = res["path"]

    # Append new section
    app_res = temp_wiki.append_note(
        relative_path=rel_path,
        content="Evening summary: all tasks merged.",
        heading="Evening Update",
    )
    assert app_res["success"] is True
    assert app_res["word_count"] > 3
    assert len(app_res["content_hash"]) == 16

    # Read note back
    read_res = temp_wiki.read_note(rel_path)
    assert "## Evening Update" in read_res["content"]
    assert "Evening summary: all tasks merged." in read_res["content"]
    assert "Morning check-in complete." in read_res["content"]


def test_read_note_includes_backlinks(temp_wiki):
    """Verify read_note extracts incoming backlinks [CARD-125]."""
    # Note B
    res_b = temp_wiki.file_note(
        title="Database Architecture",
        content="SQLite WAL mode and schema definitions.",
        domain="systems_engineering",
        topic="storage",
    )
    # Note A linking to Note B
    temp_wiki.file_note(
        title="System Design Overview",
        content="Refer to [[Database Architecture]] for storage specs.",
        domain="systems_engineering",
        topic="observability",
    )

    read_b = temp_wiki.read_note(res_b["path"])
    assert read_b["success"] is True
    assert "backlinks" in read_b
    assert any("system_design_overview" in bl for bl in read_b["backlinks"])


def test_list_notes_with_rich_metadata_filters(temp_wiki):
    """Verify list_notes filters by status, tag, author, pinned, priority [CARD-125]."""
    temp_wiki.file_note(
        title="Active Diagnostic Run",
        content="Running diagnostics...",
        domain="operations",
        topic="diagnostics",
        status="draft",
        tags=["diagnostics", "active"],
        priority="high",
        extra_meta={"author": "autoreiv", "pinned": True},
    )
    temp_wiki.file_note(
        title="Archived Log",
        content="Old log entry.",
        domain="operations",
        topic="diagnostics",
        status="archived",
        tags=["log"],
        priority="low",
        extra_meta={"author": "assistant", "pinned": False},
    )

    # Filter by status
    drafts = temp_wiki.list_notes(status="draft")
    assert len(drafts) == 1
    assert drafts[0]["title"] == "Active Diagnostic Run"

    # Filter by tag
    tagged = temp_wiki.list_notes(tag="diagnostics")
    assert len(tagged) == 1
    assert tagged[0]["title"] == "Active Diagnostic Run"

    # Filter by author
    autoreiv_notes = temp_wiki.list_notes(author="autoreiv")
    assert len(autoreiv_notes) == 1
    assert autoreiv_notes[0]["title"] == "Active Diagnostic Run"

    # Filter by pinned
    pinned_notes = temp_wiki.list_notes(pinned=True)
    assert len(pinned_notes) == 1
    assert pinned_notes[0]["title"] == "Active Diagnostic Run"


def test_cleanup_vault(temp_wiki):
    """Verify cleanup_vault removes duplicate templates from notes/ and organizes worklogs [CARD-125]."""
    root = temp_wiki.root_dir

    # Simulate misplaced template in notes/
    bad_template_dir = root / "notes" / "weekly" / "templates"
    bad_template_dir.mkdir(parents=True, exist_ok=True)
    (bad_template_dir / "Weekly Notes Template.md").write_text("template", encoding="utf-8")

    # Simulate weekly note in legacy location
    (root / "notes" / "weekly" / "2026-W35.md").write_text("# Week 35", encoding="utf-8")

    # Run cleanup
    cleanup_res = temp_wiki.cleanup_vault()
    assert cleanup_res["success"] is True

    # Bad template removed from notes/
    assert not (bad_template_dir / "Weekly Notes Template.md").exists()

    # Weekly note moved to operations/worklog/
    assert (root / "notes" / "operations" / "worklog" / "2026-W35.md").exists()

    # Canonical template exists in resources/templates/
    assert (root / "resources" / "templates" / "note_template.md").exists()
