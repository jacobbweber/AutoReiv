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
        "using the `handoff_to_agent` tool, and summarize their findings back to the user."
    ),
    purpose=ModelPurpose.GENERAL,
    tone=AgentTone.FRIENDLY,
    avatar_icon="bot",
    model="default",
    allowed_tool_names=[
        "get_or_create_weekly_note",
        "log_daily_work_item",
        "complete_weekly_task",
        "rollover_weekly_tasks",
        "get_weekly_summary",
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "wiki_overview",
        "wiki_graph",
        "handoff_to_agent",
        "lookup_agents",
        "batch_worker_scan",
        "get_session_artifact",
        "promote_artifact_to_wiki",
    ],
    pinned_tool_names=["handoff_to_agent"],
    max_active_tools=6,
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
        "You run directly on the host system. When querying host hardware, hostname, or IP addresses, "
        "always use `system_info` first to retrieve accurate telemetry. When executing commands via `cli_exec`, "
        "always use commands matching the host OS (e.g. `ipconfig`, `netstat`, or PowerShell on Windows; `ip addr` or bash on Linux). "
        "You can also document findings or architecture notes in the Wiki (`wiki_note_create`, `wiki_note_read`)."
    ),
    purpose=ModelPurpose.GENERAL,
    tone=AgentTone.CONCISE,
    avatar_icon="terminal",
    model="default",
    allowed_tool_names=[
        "system_info",
        "cli_exec",
        "get_recent_errors",
        "inspect_system_health",
        "get_tool_health_matrix",
        "get_system_logs",
        "get_session_transcript",
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_search",
        "wiki_note_list",
        "get_agent_usage_summary",
        "get_agent_sessions",
        "test_provider_connectivity",
        "list_available_skills_and_tools",
        "propose_agent_specification",
        "save_agent_specification",
        "wiki_overview",
        "wiki_graph",
        "handoff_to_agent",
        "lookup_agents",
        "batch_worker_scan",
        "get_session_artifact",
        "promote_artifact_to_wiki",
    ],
    pinned_tool_names=["system_info", "get_recent_errors", "cli_exec"],
    max_active_tools=6,
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
