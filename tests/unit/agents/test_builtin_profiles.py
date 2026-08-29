"""
Unit tests for Built-in Agent Profiles [REQ-AGENTS-001, REQ-AGENTS-010].
"""

from src.domain.agents.profiles import (
    ASSISTANT_PROFILE,
    AUTOREIV_PROFILE,
    BUILTIN_PROFILES,
    CODING_PROFILE,
    CONDUCTOR_PROFILE,
    REVIEW_PROFILE,
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
    assert "execute_code" not in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names


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
    assert "execute_code" not in agent.allowed_tool_names


def test_coding_profile_definition():
    agent = CODING_PROFILE
    assert agent.id == "coding"
    assert agent.name == "Coding"
    assert agent.tone == AgentTone.TECHNICAL
    assert agent.is_builtin is True
    assert "execute_code" in agent.allowed_tool_names
    assert "execute_code" in agent.pinned_tool_names
    assert "handoff_to_agent" in agent.allowed_tool_names
    assert "lookup_agents" in agent.allowed_tool_names
    assert "wiki_note_read" in agent.allowed_tool_names
    assert "wiki_note_search" in agent.allowed_tool_names
    assert "wiki_note_list" in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names
    assert "wiki_note_create" not in agent.allowed_tool_names
    assert "wiki_note_update" not in agent.allowed_tool_names
    assert "list_available_skills_and_tools" not in agent.allowed_tool_names
    assert len(agent.allowed_tool_names) < 12


def test_execute_code_only_on_coding():
    coding_ids = {p.id for p in BUILTIN_PROFILES if "execute_code" in p.allowed_tool_names}
    assert coding_ids == {"coding"}
    assert "execute_code" not in ASSISTANT_PROFILE.allowed_tool_names
    assert "execute_code" not in AUTOREIV_PROFILE.allowed_tool_names


def test_builtin_profiles_collection():
    assert len(BUILTIN_PROFILES) == 5
    ids = [a.id for a in BUILTIN_PROFILES]
    assert "assistant" in ids
    assert "autoreiv" in ids
    assert "coding" in ids
    assert "conductor" in ids
    assert "review" in ids


def test_conductor_profile_definition():
    agent = CONDUCTOR_PROFILE
    assert agent.id == "conductor"
    assert agent.name == "Conductor"
    assert agent.tone == AgentTone.FRIENDLY
    assert set(agent.allowed_tool_names) == {
        "list_cards",
        "read_card",
        "write_card",
        "set_card_status",
        "read_spec",
        "write_spec",
        "read_steering",
        "list_project_dir",
        "read_project_file",
        "handoff_to_agent",
        "lookup_agents",
    }
    assert "write_card" in agent.pinned_tool_names
    assert "handoff_to_agent" in agent.pinned_tool_names
    assert "execute_code" not in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names
    assert "write_project_file" not in agent.allowed_tool_names
    assert len(agent.allowed_tool_names) < 12



def test_review_profile_definition():
    agent = REVIEW_PROFILE
    assert agent.id == "review"
    assert agent.name == "Review"
    assert set(agent.allowed_tool_names) == {
        "list_cards",
        "read_card",
        "read_spec",
        "read_steering",
        "list_project_dir",
        "read_project_file",
        "set_card_status",
        "handoff_to_agent",
        "lookup_agents",
    }
    assert agent.pinned_tool_names == ["set_card_status"]
    assert "execute_code" not in agent.allowed_tool_names
    assert "write_card" not in agent.allowed_tool_names
    assert "write_spec" not in agent.allowed_tool_names
    assert "write_project_file" not in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names
    assert len(agent.allowed_tool_names) < 12


def test_get_builtin_profile_lookup_and_aliases():
    # Direct lookup
    assert get_builtin_profile("assistant") is not None
    assert get_builtin_profile("autoreiv") is not None
    assert get_builtin_profile("coding") is not None
    assert get_builtin_profile("coding").id == "coding"
    assert get_builtin_profile("conductor").id == "conductor"
    assert get_builtin_profile("product").id == "conductor"
    assert get_builtin_profile("plan").id == "conductor"
    assert get_builtin_profile("scrum").id == "conductor"
    assert get_builtin_profile("review").id == "review"
    assert get_builtin_profile("qa").id == "review"
    assert get_builtin_profile("tester").id == "review"

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
