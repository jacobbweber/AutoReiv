"""
Unit tests for Built-in Agent Profiles [REQ-AGENTS-001, REQ-AGENTS-010].
"""

from src.domain.agents.profiles import (
    AGENT_BUILDER_PROFILE,
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
    assert "propose_followup" in agent.allowed_tool_names
    assert "list_user_skill_packs" in agent.allowed_tool_names
    assert "skill_view" in agent.allowed_tool_names
    assert "propose_skill" in agent.allowed_tool_names
    assert "propose_tool" in agent.allowed_tool_names
    assert "propose_workflow" in agent.allowed_tool_names
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
    assert "export_agent_pack" in agent.allowed_tool_names
    assert "import_agent_pack" in agent.allowed_tool_names
    assert "scaffold_agent_pack" in agent.allowed_tool_names
    assert agent.allowed_skill == ["build-agent-pack", "recommend-capability"]
    assert "save_agent_specification" not in agent.allowed_tool_names
    assert "propose_agent_specification" in agent.allowed_tool_names
    assert "commit_skill_pack" in agent.allowed_tool_names
    assert "list_available_skills_and_tools" in agent.allowed_tool_names
    assert agent.show_in_chat is True
    assert "inspect_system_health" in agent.allowed_tool_names
    assert "get_system_logs" in agent.allowed_tool_names
    assert "get_recent_errors" in agent.allowed_tool_names
    assert "system_info" in agent.allowed_tool_names
    assert "cli_exec" in agent.allowed_tool_names
    assert "wiki_note_create" in agent.allowed_tool_names
    assert "wiki_note_read" in agent.allowed_tool_names
    assert "handoff_to_agent" in agent.allowed_tool_names
    assert "propose_followup" in agent.allowed_tool_names
    assert "list_user_skill_packs" in agent.allowed_tool_names
    assert "skill_view" in agent.allowed_tool_names
    assert "propose_skill" in agent.allowed_tool_names
    assert "propose_tool" in agent.allowed_tool_names
    assert "propose_workflow" in agent.allowed_tool_names
    assert "execute_code" not in agent.allowed_tool_names


def test_get_builtin_profile_lookup_and_aliases():
    # Direct lookup
    assert get_builtin_profile("assistant") is not None
    assert get_builtin_profile("autoreiv") is not None
    assert get_builtin_profile("coding") is None
    assert get_builtin_profile("conductor") is None
    assert get_builtin_profile("review") is None
    assert get_builtin_profile("product") is None
    assert get_builtin_profile("plan") is None
    assert get_builtin_profile("scrum") is None
    assert get_builtin_profile("qa") is None
    assert get_builtin_profile("tester") is None

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


def test_agent_builder_profile_definition():
    agent = AGENT_BUILDER_PROFILE
    assert agent.id == "agent-builder"
    assert agent.name == "Agent Builder"
    assert agent.is_builtin is True
    assert set(agent.allowed_tool_names) == {
        "list_available_skills_and_tools",
        "propose_agent_specification",
        "save_agent_specification",
        "propose_skill",
        "propose_tool",
        "propose_workflow",
        "commit_skill_pack",
        "list_user_skill_packs",
        "skill_view",
        "lookup_agents",
        "handoff_to_agent",
    }
    assert len(agent.allowed_tool_names) < 12
    assert "execute_code" not in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names
    assert "git_commit" not in agent.allowed_tool_names
    assert "write_card" not in agent.allowed_tool_names
    assert "write_spec" not in agent.allowed_tool_names
    assert "write_project_file" not in agent.allowed_tool_names
    assert "not Conductor" in agent.system_prompt or "You are not Conductor" in agent.system_prompt
    assert get_builtin_profile("agent-builder") is agent
    assert agent.show_in_chat is False


def test_sdlc_specialists_are_not_builtins():
    ids = {p.id for p in BUILTIN_PROFILES}
    assert ids == {"assistant", "autoreiv", "agent-builder"}
    assert "coding" not in ids
    assert "conductor" not in ids
    assert "review" not in ids


def test_agent_builder_hidden_from_chat_autoreiv_visible():
    assert AGENT_BUILDER_PROFILE.show_in_chat is False
    assert AUTOREIV_PROFILE.show_in_chat is True
    assert ASSISTANT_PROFILE.show_in_chat is True
