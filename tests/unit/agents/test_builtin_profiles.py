"""
Unit tests for Built-in Agent Profiles [REQ-AGENTS-001, REQ-AGENTS-010, CARD-429].
Assistant / AutoReiv are Platform Agent Packs. agent-builder is not a live builtin.
"""

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.domain.agents.profiles import (
    BUILTIN_PROFILES,
    RETIRED_LIVE_AGENT_IDS,
    canonical_agent_id,
    get_builtin_profile,
)
from src.domain.kernel.models import AgentTone
from tests.unit.agent_skills.catalog import platform_pack_profile


def test_developer_is_separate_pack_and_not_in_autoreiv():
    autoreiv = platform_pack_profile("autoreiv")
    assert autoreiv.id == "autoreiv"
    assert "sdlc-engineering" not in autoreiv.allowed_skill
    assert "cli_exec" not in list(resolve_allowed_tools(autoreiv))
    assert "handoff_to_agent" not in list(resolve_allowed_tools(autoreiv))  # CARD-596

    dev = platform_pack_profile("developer")
    assert dev.id == "developer"
    assert "implement-change" in dev.allowed_skill  # CARD-562
    assert "write_project_file" in list(resolve_allowed_tools(dev))
    assert "read_project_file" in list(resolve_allowed_tools(dev))
    assert "cli_exec" not in list(resolve_allowed_tools(dev))  # CARD-562: no shell/code runner on Developer


def test_tutor_absorbed_into_autoreiv_profile():
    agent = platform_pack_profile("autoreiv")
    assert agent.id == "autoreiv"
    assert "socratic-tutoring" not in agent.allowed_skill  # CARD-596: AutoReiv unticked education skills
    assert "wiki_note_read" in list(resolve_allowed_tools(agent))
    assert "wiki_note_search" in list(resolve_allowed_tools(agent))


def test_autoreiv_profile_definition():
    agent = platform_pack_profile("autoreiv")
    assert agent.id == "autoreiv"
    assert agent.name == "AutoReiv"
    assert agent.tone == AgentTone.CONCISE
    assert "build-agent-pack" not in agent.allowed_skill
    assert "proposals" in agent.allowed_skill
    assert "platform-health" in agent.allowed_skill
    assert "session-inspect" in agent.allowed_skill
    assert "wiki_tasks" in agent.allowed_skill
    assert "wiki-knowledge" in agent.allowed_skill
    assert "wiki-inbox" in agent.allowed_skill
    assert "wiki-curation" in agent.allowed_skill
    assert "coordination" not in agent.allowed_skill  # CARD-596
    assert "save_agent_specification" not in list(resolve_allowed_tools(agent))
    assert "propose_agent_specification" not in list(resolve_allowed_tools(agent))  # CARD-569
    assert "inspect_agent" in list(resolve_allowed_tools(agent))
    assert "commit_skill" in list(resolve_allowed_tools(agent))
    assert "list_available_skills_and_tools" in list(resolve_allowed_tools(agent))
    assert agent.show_in_chat is True
    assert "inspect_system_health" in list(resolve_allowed_tools(agent))
    assert "get_system_logs" in list(resolve_allowed_tools(agent))
    assert "get_recent_errors" in list(resolve_allowed_tools(agent))
    assert "system_info" in list(resolve_allowed_tools(agent))
    assert "cli_exec" not in list(resolve_allowed_tools(agent))
    assert "wiki_note_create" in list(resolve_allowed_tools(agent))
    assert "wiki_note_read" in list(resolve_allowed_tools(agent))
    assert "get_or_create_weekly_note" not in list(resolve_allowed_tools(agent))
    assert "log_daily_work_item" not in list(resolve_allowed_tools(agent))
    assert "complete_weekly_task" not in list(resolve_allowed_tools(agent))
    assert "rollover_weekly_tasks" not in list(resolve_allowed_tools(agent))
    assert "get_weekly_summary" not in list(resolve_allowed_tools(agent))
    assert "handoff_to_agent" not in list(resolve_allowed_tools(agent))  # CARD-596
    assert "propose_followup" not in list(resolve_allowed_tools(agent))  # CARD-596
    assert "list_user_skills" in list(resolve_allowed_tools(agent))
    assert "skill_view" in list(resolve_allowed_tools(agent))
    assert "propose_skill" in list(resolve_allowed_tools(agent))
    assert "propose_tool" in list(resolve_allowed_tools(agent))
    assert "propose_workflow" not in list(resolve_allowed_tools(agent))
    assert "execute_code" not in list(resolve_allowed_tools(agent))
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
    # CARD-562 (Jacob 2026-09-28): tool building is parked off Developer until M25 slice 2.
    for sid in ("capability-authoring", "proposals", "native-tool-engineering", "mcp-engineering"):
        assert sid not in dev.allowed_skill
    assert "coding" not in dev.allowed_skill  # CARD-562 supersedes CARD-550 D1: active project, not the checkout
    for name in (
        "list_available_skills_and_tools",
        "propose_skill",
        "propose_tool",
        "commit_skill",
    ):
        assert name not in list(resolve_allowed_tools(dev))  # CARD-562: parked until slice 2
    assert "save_agent_specification" not in list(resolve_allowed_tools(dev))
    assert "propose_workflow" not in list(resolve_allowed_tools(dev))


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
