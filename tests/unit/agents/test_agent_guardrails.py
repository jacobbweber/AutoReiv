"""
Unit tests for Deterministic Agent Profile Guardrails [REQ-SKIL-003].
"""

import pytest

from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError


def test_guardrail_valid_profile_passes():
    valid_data = {
        "id": "k8s-devops-sre",
        "name": "Kubernetes DevOps SRE",
        "description": "Specialist in container lifecycle and node diagnostics",
        "system_prompt": "You are a senior Kubernetes SRE. Your role is inspecting pods and analyzing cluster events.",
        "purpose": "task_execution",
        "tone": "technical",
        "avatar_icon": "terminal",
        "allowed_tools": ["cli_exec", "system_info"],
        "max_turns": 15,
    }
    available_tools = {"cli_exec", "system_info", "wiki_note_create"}

    profile = AgentProfileGuardrail.validate(valid_data, available_tools=available_tools)
    assert profile.id == "k8s-devops-sre"
    assert profile.allowed_tool_names == ["cli_exec", "system_info"]
    assert profile.max_turns == 15


def test_guardrail_rejects_invalid_slug():
    invalid_data = {
        "id": "Invalid Slug with Spaces!",
        "name": "Invalid Agent",
        "description": "Valid description for an invalid agent",
        "system_prompt": "You are a helpful assistant with lots of expertise.",
        "purpose": "general",
        "allowed_tools": [],
    }
    with pytest.raises(AgentValidationError, match="slug format"):
        AgentProfileGuardrail.validate(invalid_data, available_tools={"cli_exec"})


def test_guardrail_rejects_hallucinated_tools():
    hallucinated_data = {
        "id": "custom-agent",
        "name": "Custom Agent",
        "description": "Agent with hallucinated tool names",
        "system_prompt": "You are a helpful agent with access to non-existent tools.",
        "purpose": "general",
        "allowed_tools": ["cli_exec", "magical_sql_wizard_tool"],
    }
    with pytest.raises(AgentValidationError, match="magical_sql_wizard_tool"):
        AgentProfileGuardrail.validate(hallucinated_data, available_tools={"cli_exec", "system_info"})


def test_guardrail_rejects_invalid_purpose():
    bad_purpose_data = {
        "id": "custom-agent",
        "name": "Custom Agent",
        "description": "Agent with invalid purpose slot",
        "system_prompt": "You are a helpful assistant for daily tasks.",
        "purpose": "super_intelligence",
        "allowed_tools": [],
    }
    with pytest.raises(AgentValidationError, match="purpose"):
        AgentProfileGuardrail.validate(bad_purpose_data, available_tools={"cli_exec"})


def test_guardrail_rejects_out_of_bound_max_turns():
    bad_turns_data = {
        "id": "custom-agent",
        "name": "Custom Agent",
        "description": "Agent with 500 max turns",
        "system_prompt": "You are a helpful assistant that loops forever.",
        "purpose": "general",
        "allowed_tools": [],
        "max_turns": 500,
    }
    with pytest.raises(AgentValidationError, match="max_turns"):
        AgentProfileGuardrail.validate(bad_turns_data, available_tools={"cli_exec"})
