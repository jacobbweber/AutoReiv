"""
Unit tests for Multi-Dimensional Mind Map Graph Model & Extraction [REQ-MIND-002].
"""

import tempfile

import pytest

from src.domain.wiki.store import WikiStore


@pytest.fixture
def wiki_store():
    with tempfile.TemporaryDirectory() as tmp:
        store = WikiStore(root_dir=tmp)
        store.scaffold()
        yield store


def test_get_mindmap_multi_dimensional(wiki_store):
    wiki_store.file_note(
        title="Orchestrator Pattern",
        domain="information_technology",
        topic="ai_engineering",
        tags=["agents", "orchestration"],
        content="See [[Agent Memory]] for persistence details.",
    )
    wiki_store.file_note(
        title="Agent Memory",
        domain="information_technology",
        topic="ai_engineering",
        tags=["agents", "memory", "sqlite"],
        content="SQLite state storage and conversation logs.",
    )

    mindmap = wiki_store.get_mindmap(include_tags=True, include_taxonomy=True)

    # 1. Check nodes
    node_ids = {n["id"] for n in mindmap["nodes"]}
    node_types = {n["type"] for n in mindmap["nodes"]}

    assert "note" in node_types
    assert "tag" in node_types
    assert "domain" in node_types
    assert "topic" in node_types

    # Tag nodes present
    assert "tag:agents" in node_ids
    assert "tag:orchestration" in node_ids
    assert "tag:memory" in node_ids

    # Taxonomy nodes present
    assert "domain:information_technology" in node_ids
    assert "topic:information_technology:ai_engineering" in node_ids

    # 2. Check edges
    edge_types = {e["type"] for e in mindmap["edges"]}
    assert "wikilink" in edge_types
    assert "has_tag" in edge_types
    assert "in_topic" in edge_types
    assert "in_domain" in edge_types

    # Check wikilink edge
    wikilink_edges = [e for e in mindmap["edges"] if e["type"] == "wikilink"]
    assert len(wikilink_edges) == 1
    assert "orchestrator_pattern.md" in wikilink_edges[0]["source"]
    assert "agent_memory.md" in wikilink_edges[0]["target"]
