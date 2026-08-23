"""
Unit tests for Wiki Knowledge Graph & WikiLink Extraction [REQ-WIKI-004].
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


def test_graph_extraction_with_multiple_wikilinks(wiki_store):
    wiki_store.file_note(
        title="Agentic OS Overview",
        domain="information_technology",
        topic="ai_engineering",
        content="Our system is built with [[Event Bus]] and [[Tool Grants]] modules.",
    )
    wiki_store.file_note(
        title="Event Bus",
        domain="information_technology",
        topic="ai_engineering",
        content="Reactive event dispatching loop.",
    )
    wiki_store.file_note(
        title="Tool Grants",
        domain="information_technology",
        topic="ai_engineering",
        content="RBAC permission model for LLM tools.",
    )

    graph = wiki_store.get_graph()
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2

    edge_targets = [e["target_title"] for e in graph["edges"]]
    assert "Event Bus" in edge_targets
    assert "Tool Grants" in edge_targets


def test_graph_empty_when_no_notes(wiki_store):
    graph = wiki_store.get_graph()
    assert graph["nodes"] == []
    assert graph["edges"] == []
