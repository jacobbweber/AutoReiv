"""
Unit tests for Built-in Agent Profiles [REQ-AGENTS-001, REQ-AGENTS-010, CARD-429].
Assistant / AutoReiv are Platform Agent Packs. agent-builder is not a live builtin.
"""

from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    RETIRED_LIVE_AGENT_IDS,
    canonical_agent_id,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentTone
from tests.unit.agent_packs.catalog import platform_pack_profile


def test_developer_is_separate_pack_and_not_in_autoreiv():
    autoreiv = platform_pack_profile("autoreiv")
    assert autoreiv.id == "autoreiv"
    assert "sdlc-engineering" not in autoreiv.allowed_skill
    assert "cli_exec" not in autoreiv.allowed_tool_names
    assert "handoff_to_agent" in autoreiv.allowed_tool_names

    dev = platform_pack_profile("developer")
    assert dev.id == "developer"
    assert "sdlc-engineering" in dev.allowed_skill
    assert "write_project_file" in dev.allowed_tool_names
    assert "read_project_file" in dev.allowed_tool_names
    assert "cli_exec" in dev.allowed_tool_names


def test_tutor_absorbed_into_autoreiv_profile():
    agent = platform_pack_profile("autoreiv")
    assert agent.id == "autoreiv"
    assert "socratic-tutoring" in agent.allowed_skill
    assert "wiki_note_read" in agent.allowed_tool_names
    assert "wiki_note_search" in agent.allowed_tool_names


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
    assert "wiki_tasks" in agent.allowed_skill
    assert "wiki-knowledge" in agent.allowed_skill
    assert "wiki-inbox" in agent.allowed_skill
    assert "wiki-curation" in agent.allowed_skill
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
    assert "cli_exec" not in agent.allowed_tool_names
    assert "wiki_note_create" in agent.allowed_tool_names
    assert "wiki_note_read" in agent.allowed_tool_names
    assert "get_or_create_weekly_note" not in agent.allowed_tool_names
    assert "log_daily_work_item" not in agent.allowed_tool_names
    assert "complete_weekly_task" not in agent.allowed_tool_names
    assert "rollover_weekly_tasks" not in agent.allowed_tool_names
    assert "get_weekly_summary" not in agent.allowed_tool_names
    assert "handoff_to_agent" in agent.allowed_tool_names
    assert "propose_followup" in agent.allowed_tool_names
    assert "list_user_skill_packs" in agent.allowed_tool_names
    assert "skill_view" in agent.allowed_tool_names
    assert "propose_skill" in agent.allowed_tool_names
    assert "propose_tool" in agent.allowed_tool_names
    assert "propose_workflow" not in agent.allowed_tool_names
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
    assert canonical_agent_id("general-assistant") == "autoreiv"
    assert canonical_agent_id("assistant") == "autoreiv"
    assert canonical_agent_id("wiki") == "autoreiv"
    assert canonical_agent_id("librarian") == "autoreiv"
    assert canonical_agent_id("system-agent") == "autoreiv"
    assert canonical_agent_id("linux-sysadmin") == "autoreiv"
    assert canonical_agent_id("sysadmin") == "autoreiv"
    assert get_builtin_profile("unknown-agent") is None
    assert get_builtin_profile("agent-builder") is None
    assert "agent-builder" in RETIRED_LIVE_AGENT_IDS


def test_developer_owns_builder_tools_not_legacy_save():
    dev = platform_pack_profile("developer")
    assert "capability-authoring" in dev.allowed_skill
    assert "proposals" in dev.allowed_skill
    assert "build-agent-pack" in dev.allowed_skill
    for name in (
        "list_available_skills_and_tools",
        "propose_agent_specification",
        "propose_skill",
        "propose_tool",
        "commit_skill_pack",
        "scaffold_agent_pack",
    ):
        assert name in dev.allowed_tool_names
    assert "save_agent_specification" not in dev.allowed_tool_names
    assert "propose_workflow" not in dev.allowed_tool_names


def test_sdlc_specialists_are_not_builtins():
    ids = {p.id for p in BUILTIN_PROFILES}
    assert ids == set()
    assert "agent-builder" not in ids
    assert "assistant" not in ids
    assert "autoreiv" not in ids
    assert "coding" not in ids
    assert "conductor" not in ids
    assert "review" not in ids


def test_agent_builder_hidden_from_chat_platform_packs_visible():
    assert get_builtin_profile("agent-builder") is None
    assert platform_pack_profile("autoreiv").show_in_chat is True
    assert platform_pack_profile("direct").show_in_chat is True
    assert platform_pack_profile("developer").show_in_chat is True
    assert platform_pack_profile("tutor").show_in_chat is True
