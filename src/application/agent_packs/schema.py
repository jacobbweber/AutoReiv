"""Agent Pack schema. Packaging of one specialist, not a fourth primitive."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PACK_SCHEMA_VERSION = "1.1"

# Never copy these into a pack (instance data / secrets / tool source).
FORBIDDEN_PACK_KEYS = frozenset(
    {
        "input_packet_json",
        "output_packet_json",
        "transcripts",
        "transcript",
        "secrets",
        "secret",
        "instance_facts",
        "episodic_facts",
    }
)
SKIP_PACK_SUFFIXES = frozenset({".py", ".pyc", ".pyo", ".pyd", ".so", ".dll", ".db", ".db-wal", ".db-shm"})


# Retired from Agent Training Factory runtime (CARD-171). Kept empty so nothing
# treats persona packs as the Factory. Packs may remain on disk unused.
FACTORY_PACK_IDS = frozenset()
RETIRED_FACTORY_PERSONA_PACK_IDS = frozenset({"conductor", "inspector", "coder", "sandbox_runner", "critic"})

# CARD-339 / CARD-341 / CARD-366 / CARD-388: Platform agent consolidation & restoration.
# autoreiv, direct, developer, tutor are the platform packs.
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
# Stale hide overrides must not win for these human-facing companions.
CHAT_SHOWN_BY_ID = frozenset({"autoreiv", "direct", "developer", "tutor"})

# Initial Factory Seed Agent Packs (repo platform-packs/ -> $DATA_DIR/packs/).
# All seeded packs are simply agent packs once installed.
DEFAULT_SEEDED_PACK_IDS = frozenset({"autoreiv", "direct", "developer", "tutor"})
PLATFORM_PACK_IDS = DEFAULT_SEEDED_PACK_IDS  # Backward compatibility alias


PLATFORM_SKILL_TOOLS: dict[str, tuple[str, ...]] = {
    "wiki": (
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "list_wiki_templates",
        "wiki_template_list",
        "wiki_template_read",
        "wiki_template_create",
        "wiki_template_update",
        "wiki_overview",
        "wiki_graph",
        "promote_artifact_to_wiki",
        "wiki_note_organize",
    ),
    "coordination": (
        "lookup_agents",
        "handoff_to_agent",
        "propose_followup",
    ),
    "proposals": (
        "propose_skill",
        "propose_tool",
        "propose_agent_specification",
        "list_available_skills_and_tools",
        "skill_view",
        "list_user_skill_packs",
        "commit_skill_pack",
    ),
    "worker": (
        "batch_worker_scan",
        "get_session_artifact",
    ),
    "sandbox": ("execute_code",),
    "sqlite-storage": (
        "query_agent_database",
        "execute_agent_database",
    ),
}

DYNAMIC_SKILL_TOOLS: dict[str, tuple[str, ...]] = {
    "diagnostics": (
        "inspect_system_health",
        "get_system_logs",
        "get_recent_errors",
        "get_tool_health_matrix",
        "cli_exec",
        "system_info",
        "test_provider_connectivity",
    ),
    "platform-health": (
        "system_info",
        "inspect_system_health",
        "get_tool_health_matrix",
        "get_recent_errors",
        "get_system_logs",
        "test_provider_connectivity",
        "cli_exec",
    ),
    "tasks": (
        "get_or_create_weekly_note",
        "log_daily_work_item",
        "complete_weekly_task",
        "rollover_weekly_tasks",
        "get_weekly_summary",
    ),
    "wiki": (
        "wiki_note_create",
        "wiki_note_read",
        "wiki_note_update",
        "wiki_note_search",
        "wiki_note_list",
        "wiki_note_organize",
        "list_wiki_templates",
        "wiki_template_list",
        "wiki_template_read",
        "wiki_template_create",
        "wiki_template_update",
        "wiki_overview",
        "wiki_graph",
        "promote_artifact_to_wiki",
    ),
    "coding": (
        "repo_file_read",
        "repo_file_list",
        "repo_file_write",
        "repo_file_patch",
    ),
    "build-agent-pack": (
        "export_agent_pack",
        "import_agent_pack",
        "scaffold_agent_pack",
    ),
    "session-inspect": (
        "get_session_transcript",
        "get_agent_sessions",
        "get_agent_usage_summary",
    ),
    "sqlite-storage": (
        "query_agent_database",
        "execute_agent_database",
    ),
}


class SkillTier(str, Enum):
    REQUIRED_PLATFORM = "required_platform"
    OPTIONAL_PLATFORM = "optional_platform"
    AGENT_PACK = "agent_pack"


# Tier 1: Enforced Platform Required Skills & Tools (CARD-339, ADR-0052)
REQUIRED_PLATFORM_SKILL_TOOLS: dict[str, tuple[str, ...]] = {
    "platform_base": (
        "activate_skill",
        "ask_clarification",
        "handoff_to_agent",
        "lookup_agents",
        "get_session_info",
    ),
}
REQUIRED_PLATFORM_SKILLS: tuple[str, ...] = tuple(REQUIRED_PLATFORM_SKILL_TOOLS.keys())
REQUIRED_PLATFORM_TOOLS: tuple[str, ...] = (
    "activate_skill",
    "ask_clarification",
    "handoff_to_agent",
    "lookup_agents",
    "get_session_info",
)

# Tier 2: Platform Optional Skills
OPTIONAL_PLATFORM_SKILLS: tuple[str, ...] = (
    "wiki",
    "coordination",
    "worker",
    "proposals",
    "sandbox",
    "sqlite-storage",
)

PLATFORM_SKILL_IDS = tuple(PLATFORM_SKILL_TOOLS.keys())
WIKI_TOOL_NAMES: tuple[str, ...] = PLATFORM_SKILL_TOOLS["wiki"]

PLATFORM_SKILL_METADATA: dict[str, dict[str, str]] = {
    "wiki": {
        "name": "Wiki & Knowledge Vault",
        "description": "Local-first Wiki document management, structured notes, and knowledge graph indexing.",
    },
    "coordination": {
        "name": "Agent Coordination & Handoff",
        "description": "Multi-agent task delegation, peer lookup, and workflow followups.",
    },
    "worker": {
        "name": "Batch Worker & Artifacts",
        "description": "Parallel batch worker scans and session artifact retrieval.",
    },
    "proposals": {
        "name": "Capability Proposals & Discovery",
        "description": "Dynamic capability discovery, HITL proposals for skills and tools.",
    },
    "sandbox": {
        "name": "Isolated Code Sandbox",
        "description": "Guarded ephemeral code execution.",
    },
    "sqlite-storage": {
        "name": "SQLite Specialty Storage",
        "description": "Query and execute operations on private agent SQLite databases with strict security guardrails.",
    },
}


class FleetManifest(BaseModel):
    """Manifest for a consolidated multi-agent fleet suite [CARD-199, REQ-FLEET-012]."""

    model_config = ConfigDict(extra="ignore")

    schema_version: str = "1.0"
    id: str
    name: str
    description: str = ""
    lead_agent_id: str
    shared_skills: list[str] = Field(default_factory=list)
    agent_ids: list[str] = Field(default_factory=list)


def is_platform_pack(agent_id: str) -> bool:
    return (agent_id or "").strip() in PLATFORM_PACK_IDS


def tools_for_platform_skills(skill_ids: list[str] | None) -> list[str]:
    """Tool ids that belong to ticked Platform skills (not pack-owned)."""
    names: list[str] = []
    for sid in skill_ids or []:
        for tool in PLATFORM_SKILL_TOOLS.get(str(sid).strip(), ()):
            if tool not in names:
                names.append(tool)
    return names


def resolve_scoped_tools(agent: Any, active_skills: Optional[Sequence[str]] = None) -> list[str]:
    """
    Resolve authorized tool names for an agent based on dynamic scoping [CARD-339, ADR-0052]:
    1. Tier 1 (Lean Platform Baseline): activate_skill, ask_clarification, handoff_to_agent, lookup_agents, get_session_info.
    2. Tier 2 (Platform & Pack Skills): Mounted dynamically when skill id in active_skills.
       When active_skills is omitted (e.g. static catalog / API reflection), all authorized tools are returned.
    3. Tier 3 (Dedicated Agent Pack): Private tools in pack_tool_names.
    """
    agent_id = agent.get("id") if isinstance(agent, dict) else getattr(agent, "id", None)
    if agent_id == "direct":
        return []

    scoped: list[str] = list(REQUIRED_PLATFORM_TOOLS)

    if isinstance(agent, dict):
        allowed_skills = list(agent.get("allowed_skill") or agent.get("skills") or [])
        pack_tools = list(agent.get("pack_tool_names") or agent.get("pack_tools") or [])
    else:
        allowed_skills = list(getattr(agent, "allowed_skill", []) or [])
        pack_tools = list(getattr(agent, "pack_tool_names", []) or [])

    if active_skills is not None:
        effective_skills = [str(s).strip() for s in active_skills]
        # Dynamically mount tools belonging to active skills
        for sid in effective_skills:
            for tool in PLATFORM_SKILL_TOOLS.get(sid, ()):
                if tool not in scoped:
                    scoped.append(tool)
            for tool in DYNAMIC_SKILL_TOOLS.get(sid, ()):
                if tool not in scoped:
                    scoped.append(tool)

        # Check pack-declared skills from agent pack manifest
        if agent_id:
            try:
                from src.infrastructure.data.resolver import DataDirResolver
                data_root = DataDirResolver().resolve().root
                pack_json_file = data_root / "packs" / agent_id / "pack.json"
                if pack_json_file.is_file():
                    import json
                    pdata = json.loads(pack_json_file.read_text(encoding="utf-8"))
                    for sk in pdata.get("skills") or []:
                        if isinstance(sk, dict) and sk.get("id") in effective_skills:
                            for t in sk.get("tools") or []:
                                if t and t not in scoped:
                                    scoped.append(str(t))
            except Exception:
                pass
        return scoped

    # Static / unconstrained resolution: include all authorized skills & pack tools
    for sid in allowed_skills:
        clean_sid = str(sid).strip()
        for tool in PLATFORM_SKILL_TOOLS.get(clean_sid, ()):
            if tool not in scoped:
                scoped.append(tool)
        for tool in DYNAMIC_SKILL_TOOLS.get(clean_sid, ()):
            if tool not in scoped:
                scoped.append(tool)

    for tool in pack_tools:
        clean_tool = str(tool).strip()
        if clean_tool and clean_tool not in scoped:
            scoped.append(clean_tool)

    return scoped


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


def _normalize_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    seen: List[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


class PackSkill(BaseModel):
    """One skill on a pack: runbook id plus the tools that belong to it."""

    id: str
    name: str = ""
    description: str = ""
    tools: List[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Skill id cannot be empty.")
        return cleaned

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_optional_str(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("tools", mode="before")
    @classmethod
    def normalize_tools(cls, value: Any) -> List[str]:
        return _normalize_str_list(value)


class PackStorageConfig(BaseModel):
    """Storage settings for an agent pack [CARD-148]."""

    enabled: bool = False
    type: str = "sqlite"


class PackMemoryConfig(BaseModel):
    """Cognitive memory settings for an agent pack [CARD-116]."""

    enabled: bool = True
    retention_days: int = 30
    pinned_memory: str = ""


class PackMCPServerConfig(BaseModel):
    """MCP Server settings for an agent pack [CARD-176, CARD-183, REQ-DELIV-004, REQ-MCP-AGENT-001]."""

    name: Optional[str] = None
    enabled: bool = False
    entrypoint: str = "mcp/server.py"
    transport: str = "stdio"  # "stdio" | "sse"
    url: Optional[str] = None
    command: Optional[List[str]] = None
    headers: Optional[dict[str, str]] = None
    env: Optional[dict[str, str]] = None


class AgentPackManifest(BaseModel):
    """pack.json for one specialist: identity, nested skills, pack-owned tool ids, Show in Chat."""

    schema_version: str = PACK_SCHEMA_VERSION
    id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    tone: str = "default"
    provider: str = "default"
    purpose: str = "general"
    avatar_icon: str = "bot"
    model: str = "default"
    skills: List[PackSkill] = Field(default_factory=list)
    allowed_skill: List[str] = Field(default_factory=list)
    pack_tool_names: List[str] = Field(default_factory=list)
    show_in_chat: bool = True
    visibility: str = "public"
    fleet: Optional[str] = None
    storage: Optional[PackStorageConfig] = None
    storage_enabled: bool = False
    storage_type: str = "sqlite"
    memory: Optional[PackMemoryConfig] = None
    memory_enabled: bool = True
    memory_retention_days: int = 30
    pinned_memory: str = ""
    mcp_server: Optional[PackMCPServerConfig] = None
    mcp_servers: List[PackMCPServerConfig] = Field(default_factory=list)
    allow_autonomous_training: bool = False
    max_training_retries: int = 2
    allow_wiki_access: bool = True
    allowed_credentials: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator("id")
    @classmethod
    def validate_id_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Pack id cannot be empty.")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Pack name cannot be empty.")
        return cleaned

    @field_validator("purpose", mode="before")
    @classmethod
    def normalize_purpose(cls, value: Any) -> str:
        val = str(value or "general").strip().lower()
        if val == "code":
            return "task_execution"
        return val or "general"

    @field_validator("allowed_skill", "pack_tool_names", "allowed_credentials", mode="before")
    @classmethod
    def normalize_str_list(cls, value: Any) -> List[str]:
        return _normalize_str_list(value)

    @model_validator(mode="after")
    def derive_compat_lists(self) -> AgentPackManifest:
        nested_ids = [skill.id for skill in self.skills if skill.id]
        if nested_ids:
            merged_ids = list(nested_ids)
            for sid in self.allowed_skill:
                if sid not in merged_ids:
                    merged_ids.append(sid)
            self.allowed_skill = merged_ids
            # Extra allowed_skill ids (e.g. Platform skill wiki) stay ticked but are not pack-owned.
        elif self.allowed_skill:
            self.skills = [PackSkill(id=sid, tools=[]) for sid in self.allowed_skill if sid not in PLATFORM_SKILL_IDS]

        nested_tools: List[str] = []
        for skill in self.skills:
            for tool in skill.tools:
                if tool not in nested_tools:
                    nested_tools.append(tool)
        merged_tools = list(nested_tools)
        for name in self.pack_tool_names:
            if name not in merged_tools:
                merged_tools.append(name)
        self.pack_tool_names = merged_tools

        if self.storage is not None:
            self.storage_enabled = bool(self.storage.enabled)
            self.storage_type = str(self.storage.type or "sqlite")
        elif self.storage_enabled:
            self.storage = PackStorageConfig(enabled=True, type=self.storage_type or "sqlite")

        if self.memory is not None:
            self.memory_enabled = bool(self.memory.enabled)
            self.memory_retention_days = int(self.memory.retention_days)
            self.pinned_memory = str(self.memory.pinned_memory or "")
        else:
            self.memory = PackMemoryConfig(
                enabled=self.memory_enabled,
                retention_days=self.memory_retention_days,
                pinned_memory=self.pinned_memory,
            )

        if self.visibility == "internal":
            self.show_in_chat = False
        elif self.show_in_chat is False and self.visibility == "public":
            self.visibility = "internal"

        return self
