"""
Unit tests for Wiki Structured Templates & Optional Directives [CARD-178, REQ-WIKI-030 - REQ-WIKI-037].
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


def test_scaffold_seeds_core_templates(temp_wiki):
    """Verify scaffold seeds the 6 core templates in 02_Resources/_Templates/ [REQ-WIKI-030]."""
    tmpl_dir = temp_wiki.root_dir / "02_Resources" / "_Templates"
    assert tmpl_dir.exists()

    expected_templates = [
        "feynman-technique.md",
        "concept-map-system-hub.md",
        "dikw-pyramid-of-insight.md",
        "zettelkasten-atomic.md",
        "sop-runbook.md",
        "adr-decision.md",
    ]

    for tmpl in expected_templates:
        tmpl_file = tmpl_dir / tmpl
        assert tmpl_file.exists(), f"Expected template file {tmpl} does not exist in {tmpl_dir}"
        content = tmpl_file.read_text(encoding="utf-8")
        assert len(content) > 50


def test_list_templates_returns_metadata_and_excludes_tag_authority(temp_wiki):
    """Verify list_templates returns metadata for all templates and excludes tag-authority.md [REQ-WIKI-031]."""
    templates = temp_wiki.list_templates()
    assert isinstance(templates, list)
    assert len(templates) >= 6

    slugs = [t["slug"] for t in templates]
    assert "tag-authority" not in slugs
    assert "feynman-technique" in slugs
    assert "concept-map-system-hub" in slugs
    assert "dikw-pyramid-of-insight" in slugs
    assert "zettelkasten-atomic" in slugs
    assert "sop-runbook" in slugs
    assert "adr-decision" in slugs

    feynman = next(t for t in templates if t["slug"] == "feynman-technique")
    assert feynman["title"]
    assert feynman["description"]
    assert "Step 1: Teach It" in feynman["content"] or "Analogy" in feynman["content"]


def test_get_template_by_slug(temp_wiki):
    """Verify get_template retrieves specific template skeleton [REQ-WIKI-031]."""
    res = temp_wiki.get_template("sop-runbook")
    assert res is not None
    assert res["slug"] == "sop-runbook"
    assert "Prerequisites" in res["content"] or "Step-by-Step" in res["content"]

    non_existent = temp_wiki.get_template("non-existent-template")
    assert non_existent is None


def test_file_note_default_freeform_when_template_omitted(temp_wiki):
    """Verify filing note with no template uses freeform synthesis untouched [REQ-WIKI-033]."""
    freeform_text = "## Problem Overview\nCustom freeform text without any template constraints."
    res = temp_wiki.file_note(
        title="Custom Freeform Note",
        content=freeform_text,
        category="inbox",
    )
    assert res["success"] is True
    read_res = temp_wiki.read_note(res["path"])
    assert "Custom freeform text without any template constraints." in read_res["content"]


def test_wiki_tools_template_directive():
    """Verify WikiTools create_wiki_note resolves template skeleton when template slug is specified [REQ-WIKI-034]."""
    with tempfile.TemporaryDirectory() as tmp:
        from src.application.skills.wiki_tools import WikiTools

        tools = WikiTools(wiki_root=tmp)
        res = tools.create_wiki_note(
            title="Understanding Vector Clocks",
            template="feynman-technique",
        )
        assert res["success"] is True
        assert "00_Inbox" in res["path"]

        read_res = tools.read_wiki_note(res["path"])
        assert "Understanding Vector Clocks" in read_res["content"]
        assert "Feynman" in read_res["content"] or "Analogy" in read_res["content"] or "Teach It" in read_res["content"]
        assert read_res["frontmatter"].get("template") == "feynman-technique"


def test_wiki_tools_list_and_get_templates():
    """Verify WikiTools list_wiki_templates and get_wiki_template methods."""
    with tempfile.TemporaryDirectory() as tmp:
        from src.application.skills.wiki_tools import WikiTools

        tools = WikiTools(wiki_root=tmp)
        tmpls = tools.list_wiki_templates()
        assert len(tmpls) >= 6
        slugs = [t["slug"] for t in tmpls]
        assert "adr-decision" in slugs

        adr = tools.get_wiki_template("adr-decision")
        assert adr is not None
        assert "Context & Problem Statement" in adr["content"] or "Decision Outcome" in adr["content"]


def test_wiki_tools_registration():
    """Verify wiki_template_list and template param in wiki_note_create are registered."""
    with tempfile.TemporaryDirectory() as tmp:
        from src.application.kernel.tool_registry import ScopedToolRegistry
        from src.application.skills.wiki_tools import WikiTools

        tools = WikiTools(wiki_root=tmp)
        registry = ScopedToolRegistry()
        tools.register_tools(registry)

        assert "wiki_template_list" in registry._tools
        create_schema = registry._tools["wiki_note_create"].definition.parameters
        assert "template" in create_schema["properties"]

