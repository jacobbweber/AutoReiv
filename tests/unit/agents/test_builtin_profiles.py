"""
Unit tests for Built-in Agent Profiles [REQ-AGENTS-001, REQ-AGENTS-010].
Assistant / AutoReiv are Platform Agent Packs (CARD-126). Agent Builder stays a hidden builtin.
"""

from src.domain.agents.profiles import (
    AGENT_BUILDER_PROFILE,
    BUILTIN_PROFILES,
    canonical_agent_id,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentTone
from tests.unit.agent_packs.catalog import platform_pack_profile


def test_assistant_profile_definition():
    agent = platform_pack_profile("assistant")
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
    assert "list_available_skills_and_tools" in agent.allowed_tool_names
    assert "execute_code" not in agent.allowed_tool_names
    assert "cli_exec" not in agent.allowed_tool_names
    assert agent.show_in_chat is True
    assert agent.is_builtin is False
    assert "weekly-tasks" in agent.allowed_skill
    assert "wiki" in agent.allowed_skill
    assert "coordination" in agent.allowed_skill
    assert "proposals" in agent.allowed_skill


def test_autoreiv_profile_definition():
    agent = platform_pack_profile("autoreiv")
    assert agent.id == "autoreiv"
    assert agent.name == "AutoReiv"
    assert agent.tone == AgentTone.CONCISE
    assert "export_agent_pack" in agent.allowed_tool_names
    assert "import_agent_pack" in agent.allowed_tool_names
    assert "scaffold_agent_pack" in agent.allowed_tool_names
    assert "build-agent-pack" in agent.allowed_skill
    assert "proposals" in agent.allowed_skill
    assert "platform-health" in agent.allowed_skill
    assert "session-inspect" in agent.allowed_skill
    assert "wiki" in agent.allowed_skill
    assert "coordination" in agent.allowed_skill
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
    assert agent.is_builtin is False


def test_get_builtin_profile_lookup_and_aliases():
    assert get_builtin_profile("assistant") is None
    assert get_builtin_profile("autoreiv") is None
    assert get_builtin_profile("coding") is None
    assert get_builtin_profile("conductor") is None
    assert get_builtin_profile("review") is None
    assert get_builtin_profile("product") is None
    assert get_builtin_profile("plan") is None
    assert get_builtin_profile("scrum") is None
    assert get_builtin_profile("qa") is None
    assert get_builtin_profile("tester") is None
    assert canonical_agent_id("general-assistant") == "assistant"
    assert canonical_agent_id("librarian") == "assistant"
    assert canonical_agent_id("system-agent") == "autoreiv"
    assert canonical_agent_id("linux-sysadmin") == "autoreiv"
    assert canonical_agent_id("sysadmin") == "autoreiv"
    assert get_builtin_profile("unknown-agent") is None
    assert get_builtin_profile("agent-builder") is AGENT_BUILDER_PROFILE


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
    assert ids == {"agent-builder"}
    assert "assistant" not in ids
    assert "autoreiv" not in ids
    assert "coding" not in ids
    assert "conductor" not in ids
    assert "review" not in ids


def test_agent_builder_hidden_from_chat_platform_packs_visible():
    assert AGENT_BUILDER_PROFILE.show_in_chat is False
    assert platform_pack_profile("autoreiv").show_in_chat is True
    assert platform_pack_profile("assistant").show_in_chat is True
