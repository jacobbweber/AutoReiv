"""Tests for CARD-598: Wiki templates: one storage folder, agents create/list/use templates there."""

import tempfile
from pathlib import Path

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from tests.unit.agent_skills.catalog import platform_pack_profile


def test_autoreiv_allowed_tools_includes_wiki_template_tools():
    """CARD-598: AutoReiv profile has wiki-templates ticked and its allowed tools include create and update."""
    profile = platform_pack_profile("autoreiv")
    tools = set(resolve_allowed_tools(profile).names)
    assert "wiki_template_create" in tools, f"wiki_template_create missing from AutoReiv allowed tools: {sorted(tools)}"
    assert "wiki_template_update" in tools, f"wiki_template_update missing from AutoReiv allowed tools: {sorted(tools)}"
    assert "wiki_template_list" in tools, f"wiki_template_list missing from AutoReiv allowed tools: {sorted(tools)}"
    assert "wiki_template_read" in tools, f"wiki_template_read missing from AutoReiv allowed tools: {sorted(tools)}"


def test_resolve_safe_path_longest_prefix_first():
    """CARD-598: _resolve_safe_path('resources/templates/x.md') resolves to 02_Resources/_Templates/x.md."""
    with tempfile.TemporaryDirectory() as tmp:
        store = WikiStore(root_dir=tmp)
        store.scaffold()
        target = store._resolve_safe_path("resources/templates/adr-decision.md")
        assert target is not None
        assert target.name == "adr-decision.md"
        assert target.parent.name == "_Templates"
        assert target.parent.parent.name == "02_Resources"


def test_wiki_note_create_refuses_template():
    """CARD-598: wiki_note_create refuses documents intended as templates and directs to wiki_template_create."""
    with tempfile.TemporaryDirectory() as tmp:
        tools = WikiTools(wiki_root=tmp)

        # 1. document_type="template"
        res1 = tools.create_wiki_note(title="Weekly Review", document_type="template", content="## Review")
        assert res1["success"] is False
        assert "wiki_template_create" in res1["error"]

        # 2. extra_frontmatter with type: template
        res2 = tools.create_wiki_note(title="Weekly Review", extra_frontmatter={"type": "template"}, content="## Review")
        assert res2["success"] is False
        assert "wiki_template_create" in res2["error"]

        # 3. title ends with "Template"
        res3 = tools.create_wiki_note(title="Cooking Recipe Template", content="## Ingredients")
        assert res3["success"] is False
        assert "wiki_template_create" in res3["error"]

        # 4. content frontmatter has type: template
        res4 = tools.create_wiki_note(
            title="Meeting Notes",
            content="---\ntitle: Meeting Notes\ntype: template\n---\n## Notes",
        )
        assert res4["success"] is False
        assert "wiki_template_create" in res4["error"]


def test_template_creation_one_location():
    """CARD-598: create_template creates strictly in 02_Resources/_Templates and nothing in 00_Inbox or 01_Notes."""
    with tempfile.TemporaryDirectory() as tmp:
        tools = WikiTools(wiki_root=tmp)
        res = tools.create_wiki_template(
            slug="meeting-summary",
            title="Meeting Summary",
            description="Summary of meetings",
            content="# ${TITLE}\n\n## Action Items",
        )
        assert res["success"] is True
        assert res["path"].replace("\\", "/") == "02_Resources/_Templates/meeting-summary.md"

        # Verify vault disk state
        inbox_files = list((Path(tmp) / "00_Inbox").glob("*.md"))
        notes_files = list((Path(tmp) / "01_Notes").rglob("*.md"))
        assert len(inbox_files) == 0, f"Nothing should be in Inbox, found: {inbox_files}"
        assert len(notes_files) == 0, f"Nothing should be in Notes, found: {notes_files}"

        # list_templates sees it
        templates = tools.wiki_template_list()
        slugs = [t["slug"] for t in templates]
        assert "meeting-summary" in slugs
