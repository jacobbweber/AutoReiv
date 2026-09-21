"""Unit tests for Developer Agent capability consolidation [CARD-181, CARD-366, REQ-CONSOL-001]."""

from src.application.agent_packs.schema import (
    CHAT_HIDDEN_BY_ID,
    PLATFORM_PACK_IDS,
    is_platform_pack,
    is_visible_in_chat,
)
from src.infrastructure.skills.platform_packs import platform_packs_root
from tests.unit.agent_packs.catalog import load_platform_manifest, platform_pack_profile


def test_developer_pack_is_restored_as_platform_pack():
    """CARD-388: developer is restored as a unified platform pack."""
    assert "developer" in PLATFORM_PACK_IDS
    assert is_platform_pack("developer")
    assert "developer" not in CHAT_HIDDEN_BY_ID
    assert is_visible_in_chat({"id": "developer", "show_in_chat": True}) is True

    manifest = load_platform_manifest("developer")
    assert manifest.id == "developer"
    assert manifest.name == "Developer"
    assert manifest.purpose == "task_execution"
    assert manifest.show_in_chat is True
    assert "sdlc-engineering" in {s.id for s in manifest.skills}

    profile = platform_pack_profile("developer")
    assert profile.id == "developer"
    assert profile.show_in_chat is True
    assert "cli_exec" in profile.allowed_tool_names
    assert "write_project_file" in profile.allowed_tool_names
    assert "sdlc-engineering" in profile.allowed_skill


def test_developer_carries_sdlc_engineering_skill():
    """CARD-407 / CARD-388: developer carries sdlc-engineering; autoreiv delegates via handoff."""
    manifest = load_platform_manifest("developer")
    assert manifest.id == "developer"
    assert "sdlc-engineering" in {s.id for s in manifest.skills}

    # Runbook exists under developer skills
    dev_root = platform_packs_root() / "developer"
    runbook = dev_root / "skills" / "sdlc-engineering" / "SKILL.md"
    assert runbook.is_file(), "Missing runbook for sdlc-engineering under developer"
    content = runbook.read_text(encoding="utf-8")
    assert len(content) > 50

    # Required developer tools in developer pack
    tools = set(manifest.pack_tool_names)
    required_tools = {
        "read_project_file",
        "write_project_file",
        "list_project_dir",
        "cli_exec",
        "execute_code",
    }
    assert required_tools <= tools


def test_autoreiv_pack_profile_delegates_developer_capabilities():
    """AutoReiv profile delegates shell/coding to developer via handoff_to_agent."""
    profile = platform_pack_profile("autoreiv")
    assert profile.id == "autoreiv"
    assert profile.show_in_chat is True
    assert "cli_exec" not in profile.allowed_tool_names
    assert "sdlc-engineering" not in profile.allowed_skill
    assert "handoff_to_agent" in profile.allowed_tool_names



def test_legacy_sdlc_trio_hidden_from_chat():
    for legacy_id in ("conductor", "coding", "review"):
        assert legacy_id in CHAT_HIDDEN_BY_ID
        assert is_visible_in_chat({"id": legacy_id, "show_in_chat": True}) is False
