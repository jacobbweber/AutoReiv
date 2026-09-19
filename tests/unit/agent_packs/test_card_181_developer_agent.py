"""Unit tests for Developer Agent capability consolidation [CARD-181, CARD-366, REQ-CONSOL-001]."""

from src.application.agent_packs.schema import (
    CHAT_HIDDEN_BY_ID,
    PLATFORM_PACK_IDS,
    is_platform_pack,
    is_visible_in_chat,
)
from src.infrastructure.skills.platform_packs import platform_packs_root
from tests.unit.agent_packs.catalog import load_platform_manifest, platform_pack_profile


def test_developer_pack_is_retired_from_platform_packs():
    """CARD-366: developer is absorbed into autoreiv; retired from platform packs."""
    assert "developer" not in PLATFORM_PACK_IDS
    assert not is_platform_pack("developer")
    assert "developer" in CHAT_HIDDEN_BY_ID
    assert is_visible_in_chat({"id": "developer", "show_in_chat": True}) is False


def test_autoreiv_carries_developer_sdlc_engineering_skill():
    """CARD-366: AutoReiv carries sdlc-engineering skill absorbing developer capabilities."""
    manifest = load_platform_manifest("autoreiv")
    assert manifest.id == "autoreiv"
    assert "sdlc-engineering" in {s.id for s in manifest.skills}

    # Runbook exists under autoreiv skills
    autoreiv_root = platform_packs_root() / "autoreiv"
    runbook = autoreiv_root / "skills" / "sdlc-engineering" / "SKILL.md"
    assert runbook.is_file(), "Missing runbook for sdlc-engineering"
    content = runbook.read_text(encoding="utf-8")
    assert len(content) > 50

    # Required developer tools in autoreiv pack
    tools = set(manifest.pack_tool_names)
    required_tools = {
        "read_project_file",
        "write_project_file",
        "list_project_dir",
        "cli_exec",
        "execute_code",
    }
    assert required_tools <= tools


def test_autoreiv_pack_profile_has_developer_capabilities():
    """AutoReiv profile includes tools and skills from developer persona."""
    profile = platform_pack_profile("autoreiv")
    assert profile.id == "autoreiv"
    assert profile.show_in_chat is True
    assert "cli_exec" in profile.allowed_tool_names
    assert "write_project_file" in profile.allowed_tool_names
    assert "sdlc-engineering" in profile.allowed_skill


def test_legacy_sdlc_trio_hidden_from_chat():
    for legacy_id in ("conductor", "coding", "review", "developer"):
        assert legacy_id in CHAT_HIDDEN_BY_ID
        assert is_visible_in_chat({"id": legacy_id, "show_in_chat": True}) is False
