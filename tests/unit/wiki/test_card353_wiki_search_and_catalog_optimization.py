"""
Unit tests for CARD-353: Wiki Search & Catalog Optimization.
Tests lightweight list_templates payloads, targeted get_template retrieval,
and focused metadata/tag search.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.application.agent_packs.schema import DYNAMIC_SKILL_TOOLS, PLATFORM_SKILL_TOOLS
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore


@pytest.fixture
def temp_wiki(tmp_path: Path) -> WikiStore:
    store = WikiStore(root_dir=tmp_path / "wiki")
    store.scaffold()
    return store


def test_list_templates_payload_is_lightweight_and_excludes_content(temp_wiki: WikiStore):
    """Verify list_templates returns strictly metadata (<2.5 KB total) and omits body content [CARD-353]."""
    templates = temp_wiki.list_templates()
    assert len(templates) >= 6

    # Verify no template contains heavy body text or raw frontmatter
    for tmpl in templates:
        assert "slug" in tmpl
        assert "title" in tmpl
        assert "description" in tmpl
        assert "path" in tmpl
        assert "tags" in tmpl
        assert "content" not in tmpl, f"Template {tmpl['slug']} leaked full 'content' body in listing"
        assert "raw_template" not in tmpl, f"Template {tmpl['slug']} leaked 'raw_template' in listing"

    # Verify total JSON payload size is tiny (< 500 bytes per template compared to legacy >6,000 bytes per template)
    json_bytes = len(json.dumps(templates).encode("utf-8"))
    avg_bytes = json_bytes / len(templates)
    assert avg_bytes < 500, f"Expected < 500 bytes per template, got {avg_bytes} bytes"
    assert json_bytes < 10000, f"Expected lightweight catalog < 10KB, got {json_bytes} bytes"


def test_get_template_returns_full_content_and_raw_template(temp_wiki: WikiStore):
    """Verify get_template retrieves complete content and raw template for specific slug [CARD-353]."""
    feynman = temp_wiki.get_template("feynman-technique")
    assert feynman is not None
    assert feynman["slug"] == "feynman-technique"
    assert "content" in feynman
    assert len(feynman["content"]) > 50
    assert "Step 1: Teach It" in feynman["content"] or "Analogy" in feynman["content"]
    assert "raw_template" in feynman
    assert "---" in feynman["raw_template"]


def test_wiki_template_read_tool_registered_in_registry():
    """Verify wiki_template_read is registered in ScopedToolRegistry [CARD-353]."""
    with tempfile.TemporaryDirectory() as tmp:
        tools = WikiTools(wiki_root=tmp)
        registry = ScopedToolRegistry()
        tools.register_tools(registry)

        assert "wiki_template_read" in registry._tools
        assert "wiki_template_list" in registry._tools

        # Read template via tool
        tools.create_wiki_template(
            slug="test-schema",
            title="Test Schema",
            description="A test schema template",
            content="# Test Schema\n- Field A\n- Field B\n",
            tags=["test"],
        )
        res = registry._tools["wiki_template_read"].handler(slug="test-schema")
        assert res is not None
        assert res["slug"] == "test-schema"
        assert "Field A" in res["content"]


def test_search_notes_focused_metadata_and_tag_filtering(temp_wiki: WikiStore):
    """Verify search_notes supports structured metadata/tag filters and caps previews [CARD-353]."""
    # Create test notes with different domains, topics, tags, and document_types
    n1 = temp_wiki.file_note(
        title="Grandma Stew",
        content="## Ingredients\n- Carrots\n- Beef\n- Broth\nSlow cook for 4 hours.",
        domain="resources",
        topic="cooking",
        category="resources",
        document_type="atomic_note",
        tags=["recipe", "cooking", "comfort-food"],
        summary="Classic hearty beef and carrot stew recipe.",
    )
    n2 = temp_wiki.file_note(
        title="Software Architecture Recipe",
        content="## Blueprint\nClean architecture pattern for microservices.",
        domain="engineering",
        topic="architecture",
        category="notes",
        document_type="decision",
        tags=["recipe", "software", "clean-code"],
        summary="A recipe for organizing clean backend domain boundaries.",
    )
    n3 = temp_wiki.file_note(
        title="Kitchen Safety Guidelines",
        content="## Safety First\nAlways use sharp knives safely and keep fire extinguishers ready.",
        domain="resources",
        topic="safety",
        category="resources",
        document_type="atomic_note",
        tags=["kitchen", "safety", "cooking"],
        summary="Standard fire and sanitation safety for home cooking.",
    )

    # 1. Filter by tag "cooking" (should match Stew and Kitchen Safety)
    res_tag = temp_wiki.search_notes(tags=["cooking"])
    paths = [r["path"] for r in res_tag]
    assert n1["path"] in paths
    assert n3["path"] in paths
    assert n2["path"] not in paths

    # 2. Filter by tag "recipe" AND domain "resources" (should match only Stew)
    res_tag_domain = temp_wiki.search_notes(tags=["recipe"], domain="resources")
    assert len(res_tag_domain) == 1
    assert res_tag_domain[0]["path"] == n1["path"]

    # 3. Filter by document_type "decision" (should match only Software Architecture Recipe)
    res_doc_type = temp_wiki.search_notes(document_type="decision")
    assert len(res_doc_type) == 1
    assert res_doc_type[0]["path"] == n2["path"]

    # 4. Search with query + tags
    res_query = temp_wiki.search_notes(query="stew", tags=["recipe"])
    assert len(res_query) >= 1
    assert res_query[0]["path"] == n1["path"]

    # 5. Verify payload economy: no full body returned, only preview/summary
    for r in res_query:
        assert "body" not in r
        assert len(r.get("preview", "")) <= 200


def test_schema_skill_tools_include_wiki_template_read():
    """Verify PLATFORM_SKILL_TOOLS and DYNAMIC_SKILL_TOOLS include wiki_template_read [CARD-353]."""
    assert "wiki_template_read" in PLATFORM_SKILL_TOOLS["wiki"]
    assert "wiki_template_read" in DYNAMIC_SKILL_TOOLS["wiki"]
