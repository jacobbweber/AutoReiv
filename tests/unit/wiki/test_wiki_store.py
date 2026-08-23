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
    """Verify scaffold creates inbox, notes, and resources folders [REQ-WIKI-001]."""
    root = temp_wiki.root_dir
    assert (root / "inbox" / "need_to_do").exists()
    assert (root / "inbox" / "should_do").exists()
    assert (root / "inbox" / "want_to_do").exists()
    assert (root / "notes").exists()
    assert (root / "resources" / "operating_manuals").exists()
    assert (root / "resources" / "templates").exists()


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
