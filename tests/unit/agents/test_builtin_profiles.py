"""
Unit tests for Built-in Dual Agent Profiles [REQ-AGENTS-001].
"""

from src.domain.agents.profiles import (
    ASSISTANT_PROFILE,
    AUTOREIV_PROFILE,
    BUILTIN_PROFILES,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentTone


def test_assistant_profile_definition():
    agent = ASSISTANT_PROFILE
    assert agent.id == "assistant"
    assert agent.name == "Assistant"
    assert agent.tone == AgentTone.FRIENDLY
    assert "get_or_create_weekly_note" in agent.allowed_tool_names
    assert "log_daily_work_item" in agent.allowed_tool_names
    assert "complete_weekly_task" in agent.allowed_tool_names
    assert "rollover_weekly_tasks" in agent.allowed_tool_names
    assert "get_weekly_summary" in agent.allowed_tool_names
    assert "wiki_note_create" in agent.allowed_tool_names
    assert "wiki_note_read" in agent.allowed_tool_names
    assert "handoff_to_agent" in agent.allowed_tool_names
    assert "delegate_task" not in agent.allowed_tool_names
    assert "lookup_agents" in agent.allowed_tool_names
    assert "lookup_agents" in agent.pinned_tool_names
    assert "list_available_skills_and_tools" not in agent.allowed_tool_names


def test_autoreiv_profile_definition():
    agent = AUTOREIV_PROFILE
    assert agent.id == "autoreiv"
    assert agent.name == "AutoReiv"
    assert agent.tone == AgentTone.CONCISE
    assert "inspect_system_health" in agent.allowed_tool_names
    assert "get_system_logs" in agent.allowed_tool_names
    assert "get_recent_errors" in agent.allowed_tool_names
    assert "system_info" in agent.allowed_tool_names
    assert "cli_exec" in agent.allowed_tool_names
    assert "list_available_skills_and_tools" not in agent.allowed_tool_names
    assert "wiki_note_create" in agent.allowed_tool_names
    assert "wiki_note_read" in agent.allowed_tool_names


def test_builtin_profiles_collection():
    assert len(BUILTIN_PROFILES) == 2
    ids = [a.id for a in BUILTIN_PROFILES]
    assert "assistant" in ids
    assert "autoreiv" in ids


def test_get_builtin_profile_lookup_and_aliases():
    # Direct lookup
    assert get_builtin_profile("assistant") is not None
    assert get_builtin_profile("autoreiv") is not None

    # Legacy Aliases
    assert get_builtin_profile("general-assistant") is not None
    assert get_builtin_profile("general-assistant").id == "assistant"
    assert get_builtin_profile("librarian") is not None
    assert get_builtin_profile("librarian").id == "assistant"
    assert get_builtin_profile("system-agent") is not None
    assert get_builtin_profile("system-agent").id == "autoreiv"
    assert get_builtin_profile("linux-sysadmin") is not None
    assert get_builtin_profile("linux-sysadmin").id == "autoreiv"
    assert get_builtin_profile("sysadmin") is not None
    assert get_builtin_profile("sysadmin").id == "autoreiv"

    assert get_builtin_profile("unknown-agent") is None
