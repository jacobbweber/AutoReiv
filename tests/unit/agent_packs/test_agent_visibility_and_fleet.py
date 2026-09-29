"""
Tests for Agent Visibility ('public' vs 'internal') and Fleet Grouping [CARD-198, REQ-FLEET-001, REQ-FLEET-002].
"""


import pytest

from src.application.agent_skills.schema import is_visible_in_chat
from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError
from src.domain.kernel.models import AgentProfile
from src.web.routers.agents import _public_agent


def test_is_visible_in_chat_respects_visibility_and_deprecated_hyperv():
    """is_visible_in_chat filters internal agents and deprecated hyperv agent."""
    public_agent = AgentProfile(
        id="custom-lead",
        name="Custom Lead",
        description="Lead agent",
        system_prompt="Lead system prompt here for tests.",
        visibility="public",
        show_in_chat=True,
    )
    assert is_visible_in_chat(public_agent) is True

    internal_agent = AgentProfile(
        id="custom-worker",
        name="Custom Worker",
        description="Internal worker",
        system_prompt="Worker system prompt here for tests.",
        visibility="internal",
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
