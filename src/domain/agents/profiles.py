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
    description="Technical writer, documentation architect, and PARA-Wiki knowledge manager.",
    system_prompt=(
        "You are AutoReiv's Librarian. You manage the user's markdown knowledge base following "
        "the PARA framework (Projects, Areas, Resources, Archives), format structured YAML frontmatter, "
        "and maintain note hygiene."
    ),
    purpose=ModelPurpose.AUXILIARY,
    tone=AgentTone.ACADEMIC,
    avatar_icon="book-open",
    model="default",
    allowed_tool_names=[
        "yaml_frontmatter_parse",
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_list",
    ],
    max_turns=10,
    is_builtin=True,
)

SYSTEM_AGENT_PROFILE = AgentProfile(
    id="system-agent",
    name="System Agent",
    description="Internal SRE, platform health inspector, and observability analyzer.",
    system_prompt=(
        "You are AutoReiv's System Agent. You inspect internal platform telemetry, analyze token usage, "
        "detect tool errors, and assist in agent construction."
    ),
    purpose=ModelPurpose.GENERAL,
    tone=AgentTone.CONCISE,
    avatar_icon="cpu",
    model="default",
    allowed_tool_names=[
        "inspect_system_health",
        "get_agent_usage_summary",
        "get_tool_health_matrix",
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
