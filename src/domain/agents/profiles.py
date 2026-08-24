"""
Built-in Agent Manifests & Profile Definitions [REQ-AGENTS-001].
"""

from typing import Dict, List, Optional

from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose

GENERAL_ASSISTANT_PROFILE = AgentProfile(
    id="general-assistant",
    name="General Assistant",
    description="Personal orchestrator, workflow coordinator, and daily task manager.",
    system_prompt=(
        "You are AutoReiv's General Assistant. You help the user organize their day, "
        "manage pending tasks, synthesize morning briefings, and coordinate assistance."
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
    ],
    max_turns=10,
    is_builtin=True,
)

LINUX_SYSADMIN_PROFILE = AgentProfile(
    id="linux-sysadmin",
    name="Linux Sysadmin",
    description="Expert Linux infrastructure engineer and server administrator.",
    system_prompt=(
        "You are AutoReiv's Linux Sysadmin. You monitor host health (CPU, RAM, disk, uptime) "
        "and execute administrative inspection routines safely."
    ),
    purpose=ModelPurpose.TASK_EXECUTION,
    tone=AgentTone.TECHNICAL,
    avatar_icon="terminal",
    model="default",
    allowed_tool_names=[
        "system_info",
        "cli_exec",
    ],
    max_turns=10,
    is_builtin=True,
)

LIBRARIAN_PROFILE = AgentProfile(
    id="librarian",
    name="Librarian",
    description="Knowledge architect, taxonomy curator, and Degree/Subject Wiki manager.",
    system_prompt=(
        "You are AutoReiv's Librarian. You manage the user's local Wiki document management system. "
        "You organize notes by Level 1 Degree Domain and Level 2 Subject Topic under notes/<domain>/<topic>/, "
        "manage inbox staging files, hydrate structured YAML frontmatter metadata (35 standard fields including "
        "title, summary, tags, document_type), and keep the library clean. To triage and organize inbox files, "
        "list inbox notes via wiki_note_list(category='inbox'), inspect them with wiki_note_read, and organize them "
        "into their permanent degree domain and topic using wiki_note_organize."
    ),
    purpose=ModelPurpose.AUXILIARY,
    tone=AgentTone.ACADEMIC,
    avatar_icon="book-open",
    model="default",
    allowed_tool_names=[
        "yaml_frontmatter_parse",
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_organize",
        "wiki_note_search",
        "wiki_note_list",
        "wiki_overview",
        "wiki_graph",
    ],
    max_turns=10,
    is_builtin=True,
)

SYSTEM_AGENT_PROFILE = AgentProfile(
    id="system-agent",
    name="System Agent",
    description="Internal SRE, platform health inspector, and error root-cause diagnostics engineer.",
    system_prompt=(
        "You are AutoReiv's System Agent. You are the internal platform SRE and diagnostic engineer. "
        "You monitor platform telemetry, inspect runtime error logs with get_recent_errors, read agent session "
        "transcripts with get_session_transcript, probe LLM provider health and network latency with test_provider_connectivity, "
        "tail live system logs with get_system_logs, and assist with platform troubleshooting and custom agent creation."
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
    ],
    max_turns=10,
    is_builtin=True,
)

AUDITOR_CRITIC_PROFILE = AgentProfile(
    id="auditor-critic",
    name="Auditor Critic",
    description="Adversarial reviewer, rigor analyzer, and QA auditor for high-stakes actions.",
    system_prompt=(
        "You are AutoReiv's Auditor Critic. You perform rigorous zero-shot adversarial reviews, "
        "challenge unverified assumptions, and assert deterministic compliance before actions are executed."
    ),
    purpose=ModelPurpose.REASONING,
    tone=AgentTone.TECHNICAL,
    avatar_icon="shield-alert",
    model="default",
    allowed_tool_names=[
        "verify_telemetry_consistency",
        "assert_json_schema",
        "validate_metric_bounds",
    ],
    max_turns=10,
    is_builtin=True,
)

BUILTIN_PROFILES: List[AgentProfile] = [
    GENERAL_ASSISTANT_PROFILE,
    LINUX_SYSADMIN_PROFILE,
    LIBRARIAN_PROFILE,
    SYSTEM_AGENT_PROFILE,
    AUDITOR_CRITIC_PROFILE,
]

_PROFILES_MAP: Dict[str, AgentProfile] = {p.id: p for p in BUILTIN_PROFILES}


def get_builtin_profile(agent_id: str) -> Optional[AgentProfile]:
    """Retrieve a built-in agent profile by its ID."""
    return _PROFILES_MAP.get(agent_id)
