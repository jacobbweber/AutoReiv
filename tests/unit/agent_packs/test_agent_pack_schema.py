"""CARD-119: Agent Pack schema roundtrip and Show in Chat default."""

from src.application.agent_packs.schema import AgentPackManifest, is_visible_in_chat
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


def test_builtins_default_show_in_chat_true():
    for profile in BUILTIN_PROFILES:
        assert profile.show_in_chat is True


def test_is_visible_in_chat_missing_field_shows():
    assert is_visible_in_chat({"id": "assistant", "name": "Assistant"}) is True
    assert is_visible_in_chat({"id": "hidden", "show_in_chat": False}) is False
    assert is_visible_in_chat({"id": "shown", "show_in_chat": True}) is True
    assert is_visible_in_chat(None) is True


def test_autoreiv_has_pack_tools_and_runbook():
    assert "export_agent_pack" in AUTOREIV_PROFILE.allowed_tool_names
    assert "import_agent_pack" in AUTOREIV_PROFILE.allowed_tool_names
    assert "scaffold_agent_pack" in AUTOREIV_PROFILE.allowed_tool_names
    assert AUTOREIV_PROFILE.allowed_skill == ["build-agent-pack"]
