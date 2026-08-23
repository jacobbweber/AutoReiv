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
        id="sysadmin",
        name="Linux Sysadmin Pack",
        description="OS inspection, process management, host metrics, and shell execution with guardrails.",
        icon="terminal",
        tool_names=["cli_exec", "system_info", "check_port"],
    ),
    SkillPackManifest(
        id="librarian",
        name="Librarian & Knowledge Pack",
        description="PARA-Wiki markdown document creation, note search, and archiving.",
        icon="book-open",
        tool_names=["wiki_note_create", "wiki_note_read", "wiki_note_search", "wiki_note_list"],
    ),
    SkillPackManifest(
        id="verification",
        name="SRE Verification & Critic Pack",
        description="Schema assertion, regex validation, and adversarial action auditing.",
        icon="shield-check",
        tool_names=["assert_json_schema", "assert_regex_match", "audit_action"],
    ),
    SkillPackManifest(
        id="planning",
        name="Plan & Execute Goal Pack",
        description="Formulates, updates, and iterates multi-phase milestone execution plans.",
        icon="list-checks",
        tool_names=["formulate_plan", "mark_plan_step_completed", "append_plan_step", "get_active_plan"],
    ),
    SkillPackManifest(
        id="agent-builder",
        name="System Architect Meta-Builder Pack",
        description="Discovers tools, proposes agent specs, and persists custom agent configurations.",
        icon="sparkles",
        tool_names=["list_available_skills_and_tools", "propose_agent_specification", "save_agent_specification"],
    ),
    SkillPackManifest(
        id="orchestration",
        name="Multi-Agent Handoff & Delegation Pack",
        description="Dispatches tasks across specialized agents with handoff envelopes.",
        icon="network",
        tool_names=["delegate_task", "handoff_task"],
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
                pack_tools.append({
                    "name": t.name,
                    "description": t.description,
                })
                assigned_tools.add(t_name)

        if pack_tools:
            result.append({
                "id": pack.id,
                "name": pack.name,
                "description": pack.description,
                "icon": pack.icon,
                "tools": pack_tools,
            })

    # Unassigned or custom MCP tools
    unassigned = [
        {"name": t.name, "description": t.description}
        for name, t in tools_by_name.items()
        if name not in assigned_tools
    ]

    if unassigned:
        result.append({
            "id": "general-custom",
            "name": "Custom & Extended Tools",
            "description": "Additional custom tools or dynamically registered MCP servers.",
            "icon": "cpu",
            "tools": unassigned,
        })

    return result
