"""CARD-746: Live dogfooding hardening for wiki CRUD mounting, skill authoring grounding/checks, and MCP engineering discovery."""

from __future__ import annotations

from pathlib import Path

from src.application.agent_skills.allowed_tools import pinned_skills, skill_tools
from src.application.orchestration.wiki_thin_grounding import is_wiki_create_ask, is_wiki_related_ask
from src.application.skills.wiki_tools import WikiTools
from src.application.tools.tool_check import ToolCheckService
from src.infrastructure.content.store import get_store


def test_card746_autoreiv_turn1_mounts_wiki_move_and_delete_and_supports_explicit_notes_path(tmp_path: Path):
    """Turn 1 pinned skills on AutoReiv include wiki_note_move and wiki_note_delete, and explicit 01_Notes paths work end-to-end."""
    store = get_store()
    autoreiv = store.agents.load("autoreiv")
    assert autoreiv is not None
    pinned = pinned_skills({"allowed_skill": autoreiv.skills})
    pinned_tool_names: set[str] = set()
    for tools in skill_tools(pinned).values():
        pinned_tool_names.update(tools)

    assert "wiki_note_create" in pinned_tool_names
    assert "wiki_note_move" in pinned_tool_names
    assert "wiki_note_delete" in pinned_tool_names

    wiki = WikiTools(wiki_root=tmp_path)
    created = wiki.create_wiki_note(
        title="TestNote",
        relative_path="01_Notes/DogfoodFolderA/TestNote.md",
        content="Short test note body.",
    )
    assert created["success"] is True
    assert created["path"].startswith("00_Inbox/")
    assert "wiki_note_move" in created.get("note", "")

    moved_a = wiki.move_wiki_note(
        source_path=created["path"],
        destination_path="01_Notes/DogfoodFolderA/TestNote.md",
    )
    assert moved_a["success"] is True
    assert (tmp_path / "01_Notes" / "DogfoodFolderA" / "TestNote.md").is_file()

    moved = wiki.move_wiki_note(
        source_path="01_Notes/DogfoodFolderA/TestNote.md",
        destination_path="01_Notes/DogfoodFolderB/TestNote.md",
    )
    assert moved["success"] is True
    assert not (tmp_path / "01_Notes" / "DogfoodFolderA").exists()
    assert (tmp_path / "01_Notes" / "DogfoodFolderB" / "TestNote.md").is_file()

    deleted = wiki.delete_wiki_note(relative_path="01_Notes/DogfoodFolderB/TestNote.md")
    assert deleted["success"] is True
    assert not (tmp_path / "01_Notes" / "DogfoodFolderB").exists()
    assert (tmp_path / "01_Notes").is_dir()


def test_card746_skill_and_mcp_authoring_prompts_do_not_trigger_wiki_thin_grounding():
    """Skill, tool, and MCP server authoring prompts that mention 'wiki' must not trigger wiki_thin_grounding."""
    skill_prompt = (
        'Create a new skill called dogfood-wiki-counter with a colocated tool count_wiki_folders '
        '(set RISK = "write" so I can approve it) that counts how many markdown files are in each '
        "top-level folder of my wiki."
    )
    run_tool_prompt = "Now run count_wiki_folders and tell me the markdown file counts for each top-level wiki folder."
    assert is_wiki_related_ask(skill_prompt) is False
    assert is_wiki_create_ask(skill_prompt) is False
    assert is_wiki_related_ask(run_tool_prompt) is False

    real_wiki_prompt = "Create a new wiki note in 00_Inbox summarizing our deployment checklist."
    assert is_wiki_related_ask(real_wiki_prompt) is True
    assert is_wiki_create_ask(real_wiki_prompt) is True


async def test_card746_static_check_rejects_sys_exit_and_capability_authoring_mounts_mcp_tools():
    """ToolCheckService rejects sys.exit() in colocated tools, and capability-authoring includes MCP engineering tools."""
    checker = ToolCheckService()
    bad_code = (
        '"""Count wiki folders."""\n'
        "import sys\n"
        "def run(wiki_root: str = '/data/wiki') -> dict:\n"
        "    sys.exit(1)\n"
        "    return {}\n"
    )
    res = await checker.check_native(
        name="count_wiki_folders",
        code=bad_code,
        parameters={"type": "object", "properties": {"wiki_root": {"type": "string"}}},
    )
    assert res.status == "failed"
    assert res.stage == "static"
    assert "sys.exit" in (res.error or "")

    from src.application.kernel.tool_registry import _tool_context
    from src.application.skills.session_skills import get_session_activated_skills
    from src.application.skills.user_catalog import UserSkillCatalog

    catalog = UserSkillCatalog(skills_dir=Path("/tmp"))
    tok = _tool_context.set(
        {
            "session_id": "sess_card746",
            "agent_id": "autoreiv",
            "allowed_skill": ["capability-authoring", "mcp-engineering"],
        }
    )
    try:
        view_res = catalog.skill_view(skill_id="capability-authoring")
    finally:
        _tool_context.reset(tok)
    assert view_res["success"] is True
    assert "mcp-engineering" in get_session_activated_skills("sess_card746")
    for mcp_tool in ("scaffold_mcp_server", "test_mcp_server", "deploy_mcp_container", "register_mcp_service"):
        assert mcp_tool in (view_res.get("activated_tools") or [])
