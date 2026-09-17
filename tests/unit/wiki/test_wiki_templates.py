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


def test_create_template_success(temp_wiki):
    """Verify create_template writes to template dir with validated frontmatter [CARD-349]."""
    res = temp_wiki.create_template(
        slug="system-architecture",
        title="System Architecture",
        description="Architecture design template.",
        content="# Architecture\n\n## Overview\nDescribe system.",
        tags=["architecture", "system"],
    )
    assert res["success"] is True
    assert "system-architecture.md" in res["path"]

    # Verify retrieval
    tmpl = temp_wiki.get_template("system-architecture")
    assert tmpl is not None
    assert tmpl["title"] == "System Architecture"
    assert tmpl["description"] == "Architecture design template."
    assert "## Overview" in tmpl["content"]

    # Verify on-disk file
    tmpl_file = temp_wiki.root_dir / res["path"]
    assert tmpl_file.exists()
    raw = tmpl_file.read_text(encoding="utf-8")
    assert "type: template" in raw


def test_create_template_collision_fails_closed(temp_wiki):
    """Verify create_template strictly fails closed if template already exists [CARD-349]."""
    # Attempt to create an already existing seeded template
    res = temp_wiki.create_template(
        slug="feynman-technique",
        title="Duplicate Feynman",
        description="Should fail",
        content="Overwritten content",
    )
    assert res["success"] is False
    assert "already exists" in res["error"].lower()

    # Verify original was untouched
    original = temp_wiki.get_template("feynman-technique")
    assert "Duplicate Feynman" != original["title"]


def test_update_template_success(temp_wiki):
    """Verify update_template modifies existing template fields cleanly [CARD-349]."""
    # First create a template
    temp_wiki.create_template(
        slug="incident-runbook",
        title="Incident Runbook",
        description="Original description",
        content="Original content",
        tags=["ops"],
    )

    # Now update it
    up_res = temp_wiki.update_template(
        slug="incident-runbook",
        title="Updated Incident Runbook",
        description="Updated description",
        content="Updated step 1 2 3",
        tags=["ops", "incident", "p1"],
    )
    assert up_res["success"] is True

    # Check updated retrieval
    tmpl = temp_wiki.get_template("incident-runbook")
    assert tmpl["title"] == "Updated Incident Runbook"
    assert tmpl["description"] == "Updated description"
    assert tmpl["content"] == "Updated step 1 2 3"


def test_update_template_missing_fails_closed(temp_wiki):
    """Verify update_template fails closed if template does not exist [CARD-349]."""
    res = temp_wiki.update_template(
        slug="non-existent-template",
        title="Does not exist",
    )
    assert res["success"] is False
    assert "not found" in res["error"].lower()


def test_wiki_tools_create_and_update_template():
    """Verify WikiTools implements wiki_template_create and wiki_template_update [CARD-349]."""
    with tempfile.TemporaryDirectory() as tmp:
        from src.application.skills.wiki_tools import WikiTools

        tools = WikiTools(wiki_root=tmp)

        # Create
        c_res = tools.create_wiki_template(
            slug="security-audit",
            title="Security Audit",
            description="Security audit checklist template",
            content="# Security Audit Checklist\n\n- [ ] Secrets scanned\n",
            tags=["security", "audit"],
        )
        assert c_res["success"] is True

        # Update
        u_res = tools.update_wiki_template(
            slug="security-audit",
            description="Updated audit description",
        )
        assert u_res["success"] is True

        # Verify
        retrieved = tools.get_wiki_template("security-audit")
        assert retrieved is not None
        assert retrieved["description"] == "Updated audit description"
        assert "# Security Audit Checklist" in retrieved["content"]


def test_wiki_tools_registration_card349():
    """Verify wiki_template_create and wiki_template_update are registered in ScopedToolRegistry [CARD-349]."""
    with tempfile.TemporaryDirectory() as tmp:
        from src.application.kernel.tool_registry import ScopedToolRegistry
        from src.application.skills.wiki_tools import WikiTools

        tools = WikiTools(wiki_root=tmp)
        registry = ScopedToolRegistry()
        tools.register_tools(registry)

        assert "wiki_template_create" in registry._tools
        assert "wiki_template_update" in registry._tools


