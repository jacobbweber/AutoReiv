"""
Agent Builder Skill [REQ-FORGE-005].
Equips the System Agent with meta-tooling to inspect system capabilities,
propose structured agent specifications, and persist new agent profiles.
"""

import re
from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry


class AgentBuilderSkill:
    """
    Skill providing agent introspection, automated specification authoring,
    and agent profile persistence.
    """

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        tool_registry: Optional[ScopedToolRegistry] = None,
    ):
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry or getattr(agent_registry, "master_tool_registry", ScopedToolRegistry())

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register agent builder tools on the provided ScopedToolRegistry."""
        registry.register_tool(
            name="list_available_skills_and_tools",
            description="List all available platform tools, purposes, and tones to assist in agent construction.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self.list_available_skills_and_tools,
        )

        registry.register_tool(
            name="propose_agent_specification",
            description="Generate a complete, structured agent specification blueprint based on role, objective, and domain.",
            parameters={
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "The target role (e.g. 'Kubernetes SRE Lead')"},
                    "objective": {"type": "string", "description": "Core mission and primary tasks"},
                    "domain": {
                        "type": "string",
                        "description": "Domain category: 'coding', 'sysadmin', 'database', 'writing', 'security', 'general'",
                    },
                },
                "required": ["role", "objective"],
            },
            handler=self.propose_agent_specification,
        )

        registry.register_tool(
            name="save_agent_specification",
            description="Validate and persist a custom agent specification into the platform registry.",
            parameters={
                "type": "object",
                "properties": {
                    "spec": {"type": "object", "description": "The complete agent specification dictionary"},
                },
                "required": ["spec"],
            },
            handler=self.save_agent_specification,
        )

    async def list_available_skills_and_tools(self, **kwargs) -> Dict[str, Any]:
        """Return catalog of available tools, model purposes, and tone directives."""
        tools_list = []
        if self.tool_registry:
            for t in self.tool_registry.list_tools():
                tools_list.append(
                    {
                        "name": t.name,
                        "description": t.description,
                    }
                )

        purposes = [p.value for p in ModelPurpose]
        tones = [t.value for t in AgentTone]

        return {
            "tools": tools_list,
            "purposes": purposes,
            "tones": tones,
            "avatars": [
                "bot",
                "terminal",
                "shield",
                "shield-alert",
                "book-open",
                "cpu",
                "database",
                "code",
                "check-circle",
                "sparkles",
            ],
        }

    async def propose_agent_specification(
        self,
        role: str,
        objective: str,
        domain: str = "general",
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a production-ready agent profile specification."""
        clean_role = role.strip()
        slug_id = re.sub(r"[^a-z0-9]+", "-", clean_role.lower()).strip("-")

        # Map domain to recommended purpose and avatar
        domain_lower = domain.lower()
        if "code" in domain_lower or "dev" in domain_lower or "data" in domain_lower or "sql" in domain_lower:
            purpose = ModelPurpose.TASK_EXECUTION.value
            tone = AgentTone.TECHNICAL.value
            avatar = "terminal" if "dev" in domain_lower else "database"
            suggested_tools = ["system_info", "cli_exec"]
        elif "audit" in domain_lower or "sec" in domain_lower or "qa" in domain_lower or "critic" in domain_lower:
            purpose = ModelPurpose.REASONING.value
            tone = AgentTone.TECHNICAL.value
            avatar = "shield-alert"
            suggested_tools = ["verify_telemetry_consistency", "assert_json_schema", "validate_metric_bounds"]
        elif "wiki" in domain_lower or "doc" in domain_lower or "write" in domain_lower:
            purpose = ModelPurpose.AUXILIARY.value
            tone = AgentTone.ACADEMIC.value
            avatar = "book-open"
            suggested_tools = ["wiki_note_create", "wiki_note_read", "wiki_note_list", "yaml_frontmatter_parse"]
        else:
            purpose = ModelPurpose.GENERAL.value
            tone = AgentTone.FRIENDLY.value
            avatar = "bot"
            suggested_tools = ["task_tracker_create", "task_tracker_list", "task_tracker_update"]

        system_prompt = (
            f"You are AutoReiv's {clean_role}. "
            f"Your mission is to {objective.strip()} "
            "Adhere to production engineering standards, verify your findings, and provide actionable responses."
        )

        return {
            "id": slug_id,
            "name": clean_role,
            "description": f"{clean_role} specialized in {objective.strip()}",
            "system_prompt": system_prompt,
            "purpose": purpose,
            "tone": tone,
            "avatar_icon": avatar,
            "model": "default",
            "allowed_tool_names": suggested_tools,
            "max_turns": 10,
        }

    async def save_agent_specification(
        self,
        spec: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Validate and register a custom agent specification."""
        agent_data = spec or kwargs
        if "spec" in agent_data and isinstance(agent_data["spec"], dict):
            agent_data = agent_data["spec"]

        purpose_val = (
            ModelPurpose(agent_data.get("purpose", "general"))
            if agent_data.get("purpose") in [p.value for p in ModelPurpose]
            else ModelPurpose.GENERAL
        )
        tone_val = (
            AgentTone(agent_data.get("tone", "default"))
            if agent_data.get("tone") in [t.value for t in AgentTone]
            else AgentTone.DEFAULT
        )

        profile = AgentProfile(
            id=agent_data["id"],
            name=agent_data["name"],
            description=agent_data.get("description", ""),
            system_prompt=agent_data["system_prompt"],
            purpose=purpose_val,
            tone=tone_val,
            avatar_icon=agent_data.get("avatar_icon", "bot"),
            model=agent_data.get("model", "default"),
            allowed_tool_names=agent_data.get("allowed_tool_names", []),
            max_turns=agent_data.get("max_turns", 10),
            is_builtin=False,
        )

        self.agent_registry.register_custom_agent(profile)
        return {
            "status": "created",
            "id": profile.id,
            "name": profile.name,
            "purpose": profile.purpose.value,
        }
