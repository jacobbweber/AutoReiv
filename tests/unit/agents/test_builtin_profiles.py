"""
Unit tests for Built-in Agent Profiles [REQ-AGENTS-001].
"""

from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    GENERAL_ASSISTANT_PROFILE,
    LIBRARIAN_PROFILE,
    LINUX_SYSADMIN_PROFILE,
    SYSTEM_AGENT_PROFILE,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentTone


def test_general_assistant_profile_definition():
    agent = GENERAL_ASSISTANT_PROFILE
    assert agent.id == "general-assistant"
    assert agent.name == "General Assistant"
    assert agent.tone == AgentTone.FRIENDLY
    assert "task_tracker_create" in agent.allowed_tool_names
    assert "task_tracker_list" in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names


def test_linux_sysadmin_profile_definition():
    agent = LINUX_SYSADMIN_PROFILE
    assert agent.id == "linux-sysadmin"
    assert agent.name == "Linux Sysadmin"
    assert agent.tone == AgentTone.TECHNICAL
    assert "system_info" in agent.allowed_tool_names
    assert "cli_exec" in agent.allowed_tool_names
    assert "task_tracker_create" not in agent.allowed_tool_names


def test_librarian_profile_definition():
    agent = LIBRARIAN_PROFILE
    assert agent.id == "librarian"
    assert agent.name == "Librarian"
    assert agent.tone == AgentTone.ACADEMIC
    assert "yaml_frontmatter_parse" in agent.allowed_tool_names
    assert "wiki_note_create" in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names


def test_system_agent_profile_definition():
    agent = SYSTEM_AGENT_PROFILE
    assert agent.id == "system-agent"
    assert agent.name == "System Agent"
    assert agent.tone == AgentTone.CONCISE
    assert "inspect_system_health" in agent.allowed_tool_names
    assert "get_agent_usage_summary" in agent.allowed_tool_names


def test_builtin_profiles_collection():
    assert len(BUILTIN_PROFILES) == 5
    ids = [a.id for a in BUILTIN_PROFILES]
    assert "general-assistant" in ids
    assert "linux-sysadmin" in ids
    assert "librarian" in ids
    assert "system-agent" in ids
    assert "auditor-critic" in ids


def test_get_builtin_profile_lookup():
    agent = get_builtin_profile("librarian")
    assert agent is not None
    assert agent.id == "librarian"

    assert get_builtin_profile("unknown-agent") is None
