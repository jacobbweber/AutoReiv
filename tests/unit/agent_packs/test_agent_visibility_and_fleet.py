"""
Tests for Agent Visibility ('public' vs 'internal') and Fleet Grouping [CARD-198, REQ-FLEET-001, REQ-FLEET-002].
"""

import tempfile

import pytest

from src.application.agent_packs.schema import AgentPackManifest, is_visible_in_chat
from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.agents import _public_agent


def test_agent_pack_manifest_visibility_defaults_and_sync():
    """AgentPackManifest defaults to public and syncs visibility with show_in_chat."""
    # Default visibility is public
    m_default = AgentPackManifest(id="test-lead", name="Test Lead")
    assert m_default.visibility == "public"
    assert m_default.show_in_chat is True
    assert m_default.fleet is None

    # Explicit internal visibility automatically forces show_in_chat to False
    m_internal = AgentPackManifest(
        id="test-worker",
        name="Test Worker",
        visibility="internal",
        fleet="homelab",
    )
    assert m_internal.visibility == "internal"
    assert m_internal.show_in_chat is False
    assert m_internal.fleet == "homelab"

    # Setting show_in_chat=False syncs visibility to internal
    m_hidden = AgentPackManifest(
        id="test-hidden",
        name="Test Hidden",
        show_in_chat=False,
    )
    assert m_hidden.visibility == "internal"
    assert m_hidden.show_in_chat is False


def test_is_visible_in_chat_respects_visibility_and_deprecated_hyperv():
    """is_visible_in_chat filters internal agents and deprecated hyperv agent."""
    public_agent = AgentProfile(
        id="homelab",
        name="Homelab Lead",
        description="Lead agent",
        system_prompt="Lead system prompt here for tests.",
        visibility="public",
        fleet="homelab",
        show_in_chat=True,
    )
    assert is_visible_in_chat(public_agent) is True

    internal_agent = AgentProfile(
        id="homelab-architect",
        name="Homelab Architect",
        description="Internal architect",
        system_prompt="Architect system prompt here for tests.",
        visibility="internal",
        fleet="homelab",
        show_in_chat=False,
    )
    assert is_visible_in_chat(internal_agent) is False

    # Deprecated hyperv agent is always hidden
    hyperv_agent = AgentProfile(
        id="hyperv",
        name="Hyper-V",
        description="Legacy agent",
        system_prompt="Legacy system prompt for hyperv agent.",
        visibility="public",
        show_in_chat=True,
    )
    assert is_visible_in_chat(hyperv_agent) is False


def test_guardrails_validate_visibility_and_fleet():
    """AgentProfileGuardrail parses and validates visibility and fleet."""
    valid_payload = {
        "id": "homelab-engineer",
        "name": "Homelab Engineer",
        "system_prompt": "You are the homelab engineer responsible for IaC.",
        "visibility": "internal",
        "fleet": "homelab",
    }
    profile = AgentProfileGuardrail.validate(valid_payload)
    assert profile.visibility == "internal"
    assert profile.fleet == "homelab"
    assert profile.show_in_chat is False

    # Invalid visibility value should raise validation error
    invalid_payload = dict(valid_payload, visibility="secret")
    with pytest.raises(AgentValidationError, match="visibility"):
        AgentProfileGuardrail.validate(invalid_payload)


def test_sqlite_persistence_of_visibility_and_fleet():
    """StateStore preserves visibility and fleet across save and list operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        store = SQLiteStateStore(db_path)
        profile = AgentProfile(
            id="homelab-admin",
            name="Homelab Admin",
            description="Operational admin",
            system_prompt="Admin system prompt for VM execution testing.",
            visibility="internal",
            fleet="homelab",
            show_in_chat=False,
        )
        store.save_custom_agent_profile(profile)

        reloaded = store.get_custom_agent_profile("homelab-admin")
        assert reloaded is not None
        assert reloaded.visibility == "internal"
        assert reloaded.fleet == "homelab"
        assert reloaded.show_in_chat is False

        all_profiles = store.list_custom_agent_profiles()
        matching = [p for p in all_profiles if p.id == "homelab-admin"]
        assert len(matching) == 1
        assert matching[0].visibility == "internal"
        assert matching[0].fleet == "homelab"
    finally:
        import os
        for sfx in ("", "-wal", "-shm"):
            try:
                os.remove(db_path + sfx)
            except OSError:
                pass


def test_public_agent_router_payload_includes_visibility_and_fleet():
    """_public_agent serializes visibility and fleet fields."""
    profile = AgentProfile(
        id="homelab-janitor",
        name="Homelab Janitor",
        description="Hygiene operator",
        system_prompt="Janitor system prompt for disk maintenance.",
        visibility="internal",
        fleet="homelab",
        show_in_chat=False,
    )
    payload = _public_agent(profile)
    assert payload["visibility"] == "internal"
    assert payload["fleet"] == "homelab"
    assert payload["show_in_chat"] is False
