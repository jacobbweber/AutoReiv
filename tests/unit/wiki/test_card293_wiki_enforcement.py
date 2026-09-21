"""Unit tests for CARD-293: Wiki Skill, Tools, Template Enforcement & Vault Grounding."""

import tempfile
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.wiki_tools import WikiTools


@pytest.fixture
def temp_wiki_tools():
    with tempfile.TemporaryDirectory() as tmp:
        tools = WikiTools(wiki_root=tmp)
        yield tools


def test_concept_comparison_template_seeded(temp_wiki_tools):
    """Verify concept-comparison.md template is seeded and retrievable [REQ-WIKI-293-006]."""
    tmpl = temp_wiki_tools.store.get_template("concept-comparison")
    assert tmpl is not None, "concept-comparison template must be registered"
    assert tmpl["slug"] == "concept-comparison"
    assert "Side-by-Side Comparison" in tmpl["content"] or "Core Concepts" in tmpl["content"]
    assert "Rule of Thumb" in tmpl["content"]


def test_create_wiki_note_enforces_default_template_when_omitted(temp_wiki_tools):
    """Verify create_wiki_note enforces template selection, falling back to zettelkasten-atomic [REQ-WIKI-293-002, REQ-WIKI-293-003]."""
    res = temp_wiki_tools.create_wiki_note(
        title="Unspecified Template Note",
        content="Freeform text without explicit template.",
    )
    assert res["success"] is True
    assert res.get("template") == "zettelkasten-atomic"

    read_res = temp_wiki_tools.read_wiki_note(res["path"])
    assert read_res["frontmatter"].get("template") == "zettelkasten-atomic"


def test_create_wiki_note_records_explicit_template_in_frontmatter(temp_wiki_tools):
    """Verify explicit template is recorded in YAML frontmatter [REQ-WIKI-293-003]."""
    res = temp_wiki_tools.create_wiki_note(
        title="UI UX Distinction",
        template="concept-comparison",
    )
    assert res["success"] is True
    assert res.get("template") == "concept-comparison"

    read_res = temp_wiki_tools.read_wiki_note(res["path"])
    assert read_res["frontmatter"].get("template") == "concept-comparison"
    assert "UI UX Distinction" in read_res["content"]
    assert "Side-by-Side Comparison" in read_res["content"] or "Core Concepts" in read_res["content"]


def test_vault_root_grounding_returned_in_envelopes(temp_wiki_tools):
    """Verify wiki tool envelopes return absolute vault_root and relative_path [REQ-WIKI-293-004]."""
    res = temp_wiki_tools.create_wiki_note(
        title="Grounded Note",
        content="Grounded content",
        template="zettelkasten-atomic",
    )
    assert res["success"] is True
    assert "vault_root" in res
    assert Path(res["vault_root"]).is_absolute()
    assert res["vault_root"] == str(temp_wiki_tools.store.root_dir.resolve())
    assert "relative_path" in res
    assert res["relative_path"] == res["path"]

    read_res = temp_wiki_tools.read_wiki_note(res["path"])
    assert read_res["success"] is True
    assert "vault_root" in read_res
    assert read_res["vault_root"] == str(temp_wiki_tools.store.root_dir.resolve())
    assert "relative_path" in read_res
    assert read_res["relative_path"] == res["path"]


def test_read_wiki_note_truncation_safety_metadata(temp_wiki_tools):
    """Verify read_wiki_note returns total_length and truncated flag [REQ-WIKI-293-005]."""
    body_text = "Detailed notes on distributed systems consensus protocols." * 20
    res = temp_wiki_tools.create_wiki_note(
        title="Consensus Protocols",
        content=body_text,
        template="zettelkasten-atomic",
    )
    read_res = temp_wiki_tools.read_wiki_note(res["path"])
    assert read_res["success"] is True
    assert "total_length" in read_res
    assert read_res["total_length"] >= len(body_text)
    assert read_res.get("truncated") is False


def test_tool_registry_exposes_template_discovery_callables(temp_wiki_tools):
    """Verify wiki_template_list is registered in tool registry and alias is pruned [CARD-409]."""
    registry = ScopedToolRegistry()
    temp_wiki_tools.register_tools(registry)

    assert "wiki_template_list" in registry._tools
    assert "list_wiki_templates" not in registry._tools
    discovered = temp_wiki_tools.wiki_template_list()
    assert isinstance(discovered, list)
    slugs = [t["slug"] for t in discovered]
    assert "concept-comparison" in slugs
    assert "zettelkasten-atomic" in slugs
