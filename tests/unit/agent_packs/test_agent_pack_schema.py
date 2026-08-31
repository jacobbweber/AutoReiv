"""CARD-119: Agent Pack schema roundtrip and Show in Chat default."""

from src.application.agent_packs.schema import (
    PACK_SCHEMA_VERSION,
    AgentPackManifest,
    is_visible_in_chat,
)
from src.domain.agents.profiles import AUTOREIV_PROFILE, BUILTIN_PROFILES
from src.domain.kernel.models import AgentProfile


def test_pack_manifest_roundtrip():
    manifest = AgentPackManifest(
        id="eu-c-specialist",
        name="EUC Specialist",
        description="Endpoint specialist",
        system_prompt="You help with endpoint tasks.",
        tone="technical",
        purpose="task_execution",
        avatar_icon="cpu",
        model="default",
        allowed_skill=["user-provisioning"],
        pack_tool_names=["system_info"],
        show_in_chat=False,
        created_at="2026-08-30T00:00:00+00:00",
        updated_at="2026-08-30T00:00:00+00:00",
    )
    dumped = manifest.model_dump(mode="json")
    loaded = AgentPackManifest.model_validate(dumped)
    assert loaded.id == "eu-c-specialist"
    assert loaded.allowed_skill == ["user-provisioning"]
    assert loaded.pack_tool_names == ["system_info"]
    assert loaded.show_in_chat is False
    assert "input_packet_json" not in dumped
    assert "transcripts" not in dumped
    assert "secrets" not in dumped


def test_show_in_chat_defaults_true_on_profile():
    profile = AgentProfile(
        id="new-custom",
        name="New Custom",
        description="A custom agent",
        system_prompt="You are a custom specialist.",
    )
    assert profile.show_in_chat is True
    assert profile.pack_tool_names == []


def test_builtins_show_in_chat_agent_builder_hidden():
    for profile in BUILTIN_PROFILES:
        if profile.id == "agent-builder":
            assert profile.show_in_chat is False
        else:
            assert profile.show_in_chat is True


def test_is_visible_in_chat_missing_field_shows():
    assert is_visible_in_chat({"id": "assistant", "name": "Assistant"}) is True
    assert is_visible_in_chat({"id": "hidden", "show_in_chat": False}) is False
    assert is_visible_in_chat({"id": "shown", "show_in_chat": True}) is True
    assert is_visible_in_chat(None) is True


def test_is_visible_in_chat_never_shows_agent_builder():
    assert is_visible_in_chat({"id": "agent-builder", "show_in_chat": True}) is False
    assert is_visible_in_chat({"id": "agent-builder", "show_in_chat": False}) is False
    assert is_visible_in_chat({"id": "agent-builder"}) is False


def test_autoreiv_has_pack_tools_and_runbook():
    assert "export_agent_pack" in AUTOREIV_PROFILE.allowed_tool_names
    assert "import_agent_pack" in AUTOREIV_PROFILE.allowed_tool_names
    assert "scaffold_agent_pack" in AUTOREIV_PROFILE.allowed_tool_names
    assert AUTOREIV_PROFILE.allowed_skill == ["build-agent-pack", "recommend-capability"]
    assert "save_agent_specification" not in AUTOREIV_PROFILE.allowed_tool_names


def test_pack_schema_version_is_1_1():
    assert PACK_SCHEMA_VERSION == "1.1"
    manifest = AgentPackManifest(id="x", name="X")
    assert manifest.schema_version == "1.1"


def test_nested_skills_derive_compat_lists():
    manifest = AgentPackManifest.model_validate(
        {
            "id": "eu-c-specialist",
            "name": "EUC Specialist",
            "skills": [
                {"id": "user-provisioning", "name": "User provisioning", "tools": ["system_info"]},
                {"id": "endpoint-audit", "tools": ["wiki_note_read"]},
            ],
        }
    )
    assert manifest.allowed_skill == ["user-provisioning", "endpoint-audit"]
    assert manifest.pack_tool_names == ["system_info", "wiki_note_read"]
    assert manifest.skills[0].tools == ["system_info"]
    assert manifest.skills[1].tools == ["wiki_note_read"]
    dumped = manifest.model_dump(mode="json")
    assert dumped["skills"][0]["tools"] == ["system_info"]
    assert dumped["skills"][1]["tools"] == ["wiki_note_read"]


def test_legacy_1_0_sibling_lists_still_validate():
    manifest = AgentPackManifest.model_validate(
        {
            "schema_version": "1.0",
            "id": "legacy-bot",
            "name": "Legacy Bot",
            "allowed_skill": ["user-provisioning"],
            "pack_tool_names": ["system_info"],
        }
    )
    assert manifest.allowed_skill == ["user-provisioning"]
    assert manifest.pack_tool_names == ["system_info"]
    assert manifest.skills[0].id == "user-provisioning"
    assert manifest.skills[0].tools == []


def test_leftover_top_level_tools_union_not_copied_onto_every_skill():
    manifest = AgentPackManifest.model_validate(
        {
            "id": "mixed-bot",
            "name": "Mixed Bot",
            "skills": [{"id": "alpha", "tools": ["system_info"]}],
            "pack_tool_names": ["wiki_note_read"],
        }
    )
    assert manifest.pack_tool_names == ["system_info", "wiki_note_read"]
    assert manifest.skills[0].tools == ["system_info"]
    assert all(skill.tools != manifest.pack_tool_names for skill in manifest.skills)
