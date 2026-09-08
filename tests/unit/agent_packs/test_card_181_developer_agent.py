"""Unit tests for CARD-181: Platform Core Developer Agent [REQ-DEV-001 - REQ-DEV-005]."""



from src.application.agent_packs.schema import (
    CHAT_HIDDEN_BY_ID,
    PLATFORM_PACK_IDS,
    is_platform_pack,
    is_visible_in_chat,
)
from src.infrastructure.skills.platform_packs import platform_packs_root
from tests.unit.agent_packs.catalog import load_platform_manifest, platform_pack_profile


def test_developer_pack_is_platform_pack():
    assert "developer" in PLATFORM_PACK_IDS
    assert is_platform_pack("developer")


def test_developer_pack_manifest_and_skills():
    manifest = load_platform_manifest("developer")
    assert manifest.schema_version == "1.1"
    assert manifest.id == "developer"
    assert manifest.name == "Developer"
    assert manifest.show_in_chat is True
    assert manifest.tone in ("concise", "direct")
    assert manifest.avatar_icon in ("code", "terminal")

    # Skills: plan, build, test
    skill_ids = {s.id for s in manifest.skills}
    assert skill_ids == {"plan", "build", "test"}

    # Runbooks exist on disk
    dev_root = platform_packs_root() / "developer"
    for sid in ("plan", "build", "test"):
        runbook = dev_root / "skills" / sid / "SKILL.md"
        assert runbook.is_file(), f"Missing runbook for skill {sid}"
        content = runbook.read_text(encoding="utf-8")
        assert len(content) > 50

    # Required tools
    tools = set(manifest.pack_tool_names)
    required_tools = {
        "read_project_file",
        "write_project_file",
        "list_project_dir",
        "cli_exec",
        "execute_code",
        "git_status",
        "git_diff",
        "git_branch",
        "git_commit",
        "list_cards",
        "read_card",
        "write_card",
        "set_card_status",
        "read_steering",
        "read_spec",
        "write_spec",
    }
    assert required_tools <= tools


def test_developer_pack_profile():
    profile = platform_pack_profile("developer")
    assert profile.id == "developer"
    assert profile.name == "Developer"
    assert profile.show_in_chat is True
    assert "cli_exec" in profile.allowed_tool_names
    assert "write_project_file" in profile.allowed_tool_names
    assert "plan" in profile.allowed_skill
    assert "build" in profile.allowed_skill
    assert "test" in profile.allowed_skill


def test_legacy_sdlc_trio_hidden_from_chat():
    for legacy_id in ("conductor", "coding", "review"):
        assert legacy_id in CHAT_HIDDEN_BY_ID
        assert is_visible_in_chat({"id": legacy_id, "show_in_chat": True}) is False
