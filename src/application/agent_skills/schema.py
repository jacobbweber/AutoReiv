"""Platform agent constants and the chat-visibility rule (CARD-570: no pack schema).

Agents and skills are files (``platform/agents``, ``platform/skills``); a skill's tools live only
in its SKILL.md ``tools:`` list. What stays here: the always-on platform tools, chat visibility,
retired tool names, and the capability-authoring tool set the kernel keeps off normal turns.
"""

from __future__ import annotations

from typing import Any

# Ids never listed in Chat pickers (retired personas) and ids always listed.
CHAT_HIDDEN_BY_ID = frozenset(
    {
        "agent-builder",
        "coding",
        "review",
        "conductor",
        "hyperv",
        "assistant",
        "wiki",
        "forge",
        "homelab",
        "finance",
    }
)
CHAT_SHOWN_BY_ID = frozenset({"autoreiv", "direct", "developer", "tutor", "architect"})

# Tool names removed from the platform; the capability catalog drops their rows at seed time.
RETIRED_TOOL_NAMES: tuple[str, ...] = (
    "get_or_create_weekly_note",
    "log_daily_work_item",
    "complete_weekly_task",
    "rollover_weekly_tasks",
    "get_weekly_summary",
    "list_wiki_templates",
    "get_wiki_template",
    "launch_factory_training",  # retired Factory dispatch [CARD-497 D12]
)

# Every agent with tools gets these (CARD-339, ADR-0052, CARD-539 D3).
REQUIRED_PLATFORM_TOOLS: tuple[str, ...] = (
    "activate_skill",
    "ask_clarification",
    "handoff_to_agent",
    "lookup_agents",
    "get_session_info",
    "recall_agent_memory",
    "memorize_fact",
    "read_document_file",
)

# Tool building tools (parked off Developer, CARD-562). The kernel keeps them off turns that do not ask.
CAPABILITY_AUTHORING_TOOL_NAMES = frozenset(
    {
        "list_available_skills_and_tools",
        "propose_skill",
        "propose_tool",
        "commit_skill_pack",
        "list_user_skill_packs",
        "skill_view",
    }
)


def shipped_agent_ids() -> frozenset[str]:
    from src.infrastructure.content.store import get_store

    return frozenset(get_store().agents.shipped_ids())


def is_platform_pack(agent_id: str) -> bool:
    """True for a shipped agent (``platform/agents/<id>.md``). Name kept for callers."""
    return (agent_id or "").strip() in shipped_agent_ids()


def is_visible_in_chat(agent: Any) -> bool:
    """Chat picker filter. Missing field means show. Some ids are forced."""
    if agent is None:
        return True
    if isinstance(agent, dict):
        agent_id = agent.get("id")
        visibility = agent.get("visibility")
        flag = agent.get("show_in_chat", True)
    else:
        agent_id = getattr(agent, "id", None)
        visibility = getattr(agent, "visibility", None)
        flag = getattr(agent, "show_in_chat", True)
    if visibility == "internal":
        return False
    if agent_id in CHAT_HIDDEN_BY_ID:
        return False
    if agent_id in CHAT_SHOWN_BY_ID:
        return True
    return flag is not False
