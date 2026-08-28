"""
Hierarchical Skill Pack Manifests & Catalog Clustering [REQ-SKIL-001].
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.domain.gateway.models import ToolDefinition


class SkillPackManifest(BaseModel):
    id: str = Field(..., description="Unique skill pack slug")
    name: str = Field(..., description="Human-readable pack title")
    description: str = Field(..., description="Scope and capability description")
    icon: str = Field(default="cpu", description="Lucide icon name")
    tool_names: List[str] = Field(default_factory=list, description="Tool names mapped to this pack")


BUILTIN_SKILL_PACKS: List[SkillPackManifest] = [
    SkillPackManifest(
        id="tasks",
        name="Task Management Pack",
        description="Structured task creation, status updates, due dates, and priority tracking.",
        icon="check-square",
        tool_names=[
            "task_tracker_create",
            "task_tracker_list",
            "task_tracker_update",
            "task_tracker_delete",
        ],
    ),
    SkillPackManifest(
        id="wiki",
        name="Wiki & Knowledge Pack",
        description="Local-first Wiki document management, structured YAML frontmatter, and graph indexing.",
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
            "yaml_frontmatter_parse",
        ],
    ),
    SkillPackManifest(
        id="sysadmin",
        name="Linux Sysadmin Pack",
        description="OS inspection, process management, host metrics, and shell execution with guardrails.",
        icon="terminal",
        tool_names=["cli_exec", "system_info", "check_port"],
    ),
    SkillPackManifest(
        id="diagnostics",
        name="Platform SRE & Diagnostics Pack",
        description="Platform telemetry, health checks, error log inspection, and provider connectivity probing.",
        icon="cpu",
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
    SkillPackManifest(
        id="agent-builder",
        name="Agent Forge Meta-Builder Pack",
        description="Discovers tools, proposes agent specs, and persists custom agent configurations.",
        icon="sparkles",
        tool_names=["list_available_skills_and_tools", "propose_agent_specification", "save_agent_specification"],
    ),
    SkillPackManifest(
        id="orchestration",
        name="Multi-Agent Handoff & Delegation Pack",
        description="Just-in-time peer agent discovery and isolated subagent task handoffs.",
        icon="network",
        tool_names=["lookup_agents", "handoff_to_agent", "delegate_task", "handoff_task"],
    ),
    SkillPackManifest(
        id="planning",
        name="Plan & Execute Goal Pack",
        description="Formulates, updates, and iterates multi-phase milestone execution plans.",
        icon="list-checks",
        tool_names=["formulate_plan", "mark_plan_step_completed", "append_plan_step", "get_active_plan"],
    ),
    SkillPackManifest(
        id="verification",
        name="SRE Verification & Critic Pack",
        description="Schema assertion, regex validation, and adversarial action auditing.",
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
        id="worker",
        name="Batch Worker & Map-Reduce Pack",
        description="Partition massive context tasks across parallel in-memory subagents and manage session artifacts.",
        icon="layers",
        tool_names=["batch_worker_scan", "get_session_artifact", "promote_artifact_to_wiki"],
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
                    "icon": pack.icon,
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
                "icon": "plug",
                "tools": srv_tools,
            }
        )

    if other_unassigned:
        result.append(
            {
                "id": "general-custom",
                "name": "Custom & Extended Tools",
                "description": "Additional custom tools registered with the platform.",
                "icon": "cpu",
                "tools": other_unassigned,
            }
        )

    return result
