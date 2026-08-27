"""
Built-in Agent Manifests & Profile Definitions [REQ-AGENTS-001].
Consolidated Dual-Agent Architecture: Assistant & AutoReiv.
"""

from typing import Dict, List, Optional

from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose

ASSISTANT_PROFILE = AgentProfile(
    id="assistant",
    name="Assistant",
    description="Personal workflow coordinator, task manager, and day-to-day assistant.",
    system_prompt=(
        "You are AutoReiv's Assistant. You help the user organize their day, "
        "manage pending tasks, search and write knowledge notes in the Wiki, coordinate workflows, "
        "and assist with daily activities. When technical platform diagnostics, system health checks, "
        "or log analysis are needed, you can delegate tasks to the 'autoreiv' platform agent "
        "using the `delegate_task` or `handoff_to_agent` tools, and summarize their findings back to the user."
    ),
    purpose=ModelPurpose.GENERAL,
    tone=AgentTone.FRIENDLY,
    avatar_icon="bot",
    model="default",
    allowed_tool_names=[
        "task_tracker_create",
        "task_tracker_list",
        "task_tracker_update",
        "task_tracker_delete",
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "wiki_overview",
        "wiki_graph",
        "delegate_task",
        "handoff_to_agent",
        "lookup_agents",
    ],
    max_turns=10,
    is_builtin=True,
)


AUTOREIV_PROFILE = AgentProfile(
    id="autoreiv",
    name="AutoReiv",
    description="Platform SRE, self-introspecting architecture expert, and system diagnostics engineer.",
    system_prompt=(
        "You are AutoReiv, the self-aware platform SRE and internal system expert for the AutoReiv AI platform. "
        "You understand how AutoReiv is built, how its kernel and gateway operate, and how to inspect and diagnose "
        "its live state. You have direct access to platform telemetry, error logs (`get_recent_errors`), "
        "runtime health (`inspect_system_health`), tool reliability matrices (`get_tool_health_matrix`), "
        "live application logs (`get_system_logs`), and session transcripts (`get_session_transcript`). "
        "You can also inspect host hardware (`system_info`), execute safe administrative commands (`cli_exec`), "
        "and document findings or architecture notes in the Wiki (`wiki_note_create`, `wiki_note_read`)."
    ),
    purpose=ModelPurpose.GENERAL,
    tone=AgentTone.CONCISE,
    avatar_icon="cpu",
    model="default",
    allowed_tool_names=[
        "inspect_system_health",
        "get_agent_usage_summary",
        "get_tool_health_matrix",
        "get_recent_errors",
        "get_agent_sessions",
        "get_session_transcript",
        "test_provider_connectivity",
        "get_system_logs",
        "list_available_skills_and_tools",
        "propose_agent_specification",
        "save_agent_specification",
        "system_info",
        "cli_exec",
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "wiki_overview",
        "wiki_graph",
        "delegate_task",
        "handoff_to_agent",
        "lookup_agents",
    ],
    max_turns=10,
    is_builtin=True,
)

# Backward-compatibility alias references
GENERAL_ASSISTANT_PROFILE = ASSISTANT_PROFILE
SYSTEM_AGENT_PROFILE = AUTOREIV_PROFILE
LINUX_SYSADMIN_PROFILE = AUTOREIV_PROFILE
LIBRARIAN_PROFILE = ASSISTANT_PROFILE
AUDITOR_CRITIC_PROFILE = AUTOREIV_PROFILE

BUILTIN_PROFILES: List[AgentProfile] = [
    ASSISTANT_PROFILE,
    AUTOREIV_PROFILE,
]

_PROFILES_MAP: Dict[str, AgentProfile] = {
    "assistant": ASSISTANT_PROFILE,
    "autoreiv": AUTOREIV_PROFILE,
    # Legacy Alias mappings
    "general-assistant": ASSISTANT_PROFILE,
    "general": ASSISTANT_PROFILE,
    "system-agent": AUTOREIV_PROFILE,
    "system": AUTOREIV_PROFILE,
    "linux-sysadmin": AUTOREIV_PROFILE,
    "sysadmin": AUTOREIV_PROFILE,
    "librarian": ASSISTANT_PROFILE,
    "auditor-critic": AUTOREIV_PROFILE,
}


def get_builtin_profile(agent_id: str) -> Optional[AgentProfile]:
    """Retrieve a built-in agent profile by its ID (supporting legacy aliases)."""
    return _PROFILES_MAP.get(agent_id.lower().strip())
