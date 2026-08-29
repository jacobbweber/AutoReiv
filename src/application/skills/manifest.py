"""
Hierarchical Skill Pack Manifests & Catalog Clustering [REQ-SKIL-001, REQ-TAX-001, REQ-TAX-002].
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.domain.gateway.models import ToolDefinition


class SkillTier(BaseModel):
    id: str = Field(..., description="Unique tier slug")
    name: str = Field(..., description="Human-readable tier title")
    description: str = Field(..., description="Scope and purpose of this functional tier")
    icon: str = Field(default="layers", description="Lucide icon name")


SKILL_TIERS: List[SkillTier] = [
    SkillTier(
        id="productivity",
        name="User Knowledge & Productivity",
        description="User-facing workspace tools, knowledge vaults, task management, and large codebase audits.",
        icon="book-open",
    ),
    SkillTier(
        id="system",
        name="System Operations & Platform",
        description="Host command execution, hardware telemetry, and dedicated AutoReiv platform diagnostics.",
        icon="terminal",
    ),
    SkillTier(
        id="cognition",
        name="Agent Cognition & Runtime",
        description="Autonomous planning, multi-agent delegation, self-verification critic, and meta-agent builders.",
        icon="brain",
    ),
]


class SkillPackManifest(BaseModel):
    id: str = Field(..., description="Unique skill pack slug")
    name: str = Field(..., description="Human-readable pack title")
    description: str = Field(..., description="Scope and capability description")
    tier: str = Field(default="productivity", description="Functional tier category (productivity, system, cognition)")
    icon: str = Field(default="cpu", description="Lucide icon name")
    is_core: bool = Field(default=False, description="Whether this pack is core-dedicated to a specific agent")
    core_agent_id: Optional[str] = Field(default=None, description="Target agent ID if core-dedicated")
    tool_names: List[str] = Field(default_factory=list, description="Tool names mapped to this pack")


BUILTIN_SKILL_PACKS: List[SkillPackManifest] = [
    # ── Tier 1: User Knowledge & Productivity ──
    SkillPackManifest(
        id="wiki",
        name="Wiki & Knowledge Vault",
        description="Local-first Wiki document management, structured metadata, and knowledge graph indexing.",
        tier="productivity",
        icon="book-open",
        tool_names=[
            "wiki_note_create",
            "wiki_note_read",
            "wiki_note_update",
            "wiki_note_search",
            "wiki_note_list",
            "wiki_note_organize",
            "wiki_overview",
            "wiki_graph",
        ],
    ),
    SkillPackManifest(
        id="sdlc-cards",
        name="SDLC Cards & Specs",
        description="Project-scoped cards, specs, status machine, and steering excerpts.",
        tier="productivity",
        icon="clipboard-list",
        tool_names=[
            "list_cards",
            "read_card",
            "write_card",
            "set_card_status",
            "read_spec",
            "write_spec",
            "read_steering",
        ],
    ),
    SkillPackManifest(
        id="weekly-notes",
        name="Weekly Notes & To-Dos",
        description="Markdown-first weekly work logs, daily reminders, and automated task carry-over.",
        tier="productivity",
        icon="calendar-check",
        tool_names=[
            "get_or_create_weekly_note",
            "log_daily_work_item",
            "complete_weekly_task",
            "rollover_weekly_tasks",
            "get_weekly_summary",
        ],
    ),
    SkillPackManifest(
        id="worker",
        name="Batch Worker & Map-Reduce Pack",
        description="Partition massive context tasks across parallel in-memory subagents and manage session artifacts.",
        tier="productivity",
        icon="layers",
        tool_names=[
            "batch_worker_scan",
            "get_session_artifact",
            "promote_artifact_to_wiki",
        ],
    ),
    # ── Tier 2: System Operations & Platform ──
    SkillPackManifest(
        id="sysadmin",
        name="Host Terminal & Linux Sysadmin",
        description="OS inspection, process management, host metrics, and guarded shell command execution.",
        tier="system",
        icon="terminal",
        tool_names=["cli_exec", "system_info", "check_port"],
    ),
    SkillPackManifest(
        id="diagnostics",
        name="AutoReiv Core Platform SRE & Diagnostics",
        description="Dedicated AutoReiv platform telemetry, health checks, backend log stream, and provider connectivity probing.",
        tier="system",
        icon="cpu",
        is_core=True,
        core_agent_id="autoreiv",
        tool_names=[
            "inspect_system_health",
            "get_agent_usage_summary",
            "get_tool_health_matrix",
            "get_recent_errors",
            "get_agent_sessions",
            "get_session_transcript",
            "test_provider_connectivity",
            "get_system_logs",
        ],
    ),
    # ── Tier 3: Agent Cognition & Runtime ──
    SkillPackManifest(
        id="planning",
        name="Goal Planning Engine",
        description="Formulates, updates, and tracks multi-phase milestone execution plans during autonomous runs.",
        tier="cognition",
        icon="list-checks",
        tool_names=["formulate_plan", "mark_plan_step_completed", "append_plan_step", "get_active_plan"],
    ),
    SkillPackManifest(
        id="orchestration",
        name="Multi-Agent Handoff & Delegation",
        description="Just-in-time peer agent discovery and isolated subagent task handoffs.",
        tier="cognition",
        icon="network",
        tool_names=["lookup_agents", "handoff_to_agent"],
    ),
    SkillPackManifest(
        id="verification",
        name="Agent Logic Verification (Critic)",
        description="Programmatic JSON schema assertions, numerical boundary checks, and adversarial action auditing.",
        tier="cognition",
        icon="shield-check",
        tool_names=[
            "assert_json_schema",
            "validate_metric_bounds",
            "assert_regex_match",
            "audit_action",
            "verify_telemetry_consistency",
        ],
    ),
    SkillPackManifest(
        id="agent-builder",
        name="Agent Forge Meta-Builder",
        description="Discovers tools, proposes agent specifications, and persists custom agent configurations.",
        tier="cognition",
        icon="sparkles",
        tool_names=["list_available_skills_and_tools", "propose_agent_specification", "save_agent_specification"],
    ),
]


def get_hierarchical_skills_catalog(tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
    """
    Cluster tools into hierarchical skill packs.
    Any unmapped tools are grouped into the 'General & Custom Tools' pack.
    """
    tools_by_name: Dict[str, ToolDefinition] = {t.name: t for t in tools}
    assigned_tools = set()

    result: List[Dict[str, Any]] = []

    for pack in BUILTIN_SKILL_PACKS:
        pack_tools = []
        for t_name in pack.tool_names:
            if t_name in tools_by_name:
                t = tools_by_name[t_name]
                pack_tools.append(
                    {
                        "name": t.name,
                        "description": t.description,
                    }
                )
                assigned_tools.add(t_name)

        if pack_tools:
            result.append(
                {
                    "id": pack.id,
                    "name": pack.name,
                    "description": pack.description,
                    "tier": pack.tier,
                    "icon": pack.icon,
                    "is_core": pack.is_core,
                    "core_agent_id": pack.core_agent_id,
                    "tools": pack_tools,
                }
            )

    # Group external MCP tools into dedicated per-server packs [REQ-MCP-010]
    mcp_packs_map: Dict[str, List[Dict[str, Any]]] = {}
    other_unassigned: List[Dict[str, Any]] = []

    for name, t in tools_by_name.items():
        if name in assigned_tools:
            continue
        if name.startswith("mcp_"):
            parts = name[4:].split("_", 1)
            server_name = parts[0] if len(parts) > 1 else parts[0]
            mcp_packs_map.setdefault(server_name, []).append({"name": t.name, "description": t.description})
        else:
            other_unassigned.append({"name": t.name, "description": t.description})

    for srv_name, srv_tools in mcp_packs_map.items():
        result.append(
            {
                "id": f"mcp_{srv_name}",
                "name": f"MCP: {srv_name}",
                "description": f"External Model Context Protocol server tools provided by {srv_name}.",
                "tier": "system",
                "icon": "plug",
                "is_core": False,
                "core_agent_id": None,
                "tools": srv_tools,
            }
        )

    if other_unassigned:
        result.append(
            {
                "id": "general-custom",
                "name": "Custom & Extended Tools",
                "description": "Additional custom tools registered with the platform.",
                "tier": "productivity",
                "icon": "cpu",
                "is_core": False,
                "core_agent_id": None,
                "tools": other_unassigned,
            }
        )

    return result
