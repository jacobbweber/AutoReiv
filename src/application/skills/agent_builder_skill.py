"""
Agent Builder Skill [REQ-FORGE-005] [REQ-BUILD-001 - REQ-BUILD-008].
Equips the System Agent with meta-tooling to inspect system capabilities,
propose structured agent specifications, persist new agent profiles, and
park HITL drafts for skill / tool / workflow packs (no auto-write).
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentTone
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry


class AgentBuilderSkill:
    """
    Skill providing agent introspection, automated specification authoring,
    agent profile persistence, and HITL pack drafts.
    """

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        tool_registry: Optional[ScopedToolRegistry] = None,
        store: Any = None,
        data_dir: Optional[Union[str, Path]] = None,
    ):
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry or getattr(
            agent_registry, "master_tool_registry", ScopedToolRegistry()
        )
        self.store = store if store is not None else getattr(agent_registry, "state_store", None)
        self.data_dir = Path(data_dir) if data_dir is not None else None

    def _resolved_data_dir(self) -> Path:
        if self.data_dir is not None:
            return Path(self.data_dir)
        from src.infrastructure.data.resolver import DataDirResolver

        return DataDirResolver().resolve().root

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

        payload_fields = {
            "what": {"type": "string", "description": "What is being proposed (pack, tool, or playbook SOP)."},
            "why": {"type": "string", "description": "Why this is needed."},
            "how": {
                "type": "string",
                "description": "How it should work (playbook SOP / JSON stub). Never a Python builtin write.",
            },
            "where": {
                "type": "string",
                "description": "Destination path relative to $DATA_DIR (typically skills/<slug>/SKILL.md).",
            },
            "pack_id": {"type": "string", "description": "Target pack id (directory slug under $DATA_DIR/skills)."},
            "prefer_existing_agent_id": {
                "type": "string",
                "description": "Existing specialist to extend rather than creating a new agent.",
            },
            "new_agent_id": {
                "type": "string",
                "description": "If set, a new agent is being considered; a CARD-078 warning is attached.",
            },
        }

        registry.register_tool(
            name="propose_skill",
            description=(
                "Park a HITL draft for a skill pack (what/why/how/where). "
                "Creates a proposals row status draft. Does not write SKILL.md."
            ),
            parameters={
                "type": "object",
                "properties": {k: v for k, v in payload_fields.items()},
                "required": ["what", "why", "how", "where"],
            },
            handler=self.propose_skill,
        )

        registry.register_tool(
            name="propose_tool",
            description=(
                "Park a HITL draft for a declared tool (JSON stub). "
                "Does not write a Python module. Approve does not write disk."
            ),
            parameters={
                "type": "object",
                "properties": {
                    **payload_fields,
                    "tool_json": {
                        "type": "object",
                        "description": "JSON stub: name, description, parameters. Not a Python handler.",
                    },
                },
                "required": ["what", "why", "how", "where", "pack_id", "tool_json"],
            },
            handler=self.propose_tool,
        )

        registry.register_tool(
            name="propose_workflow",
            description=(
                "Park a HITL draft for a playbook SOP workflow. "
                "Not job-template YAML. Does not auto-run a Job."
            ),
            parameters={
                "type": "object",
                "properties": {k: v for k, v in payload_fields.items()},
                "required": ["what", "why", "how", "where"],
            },
            handler=self.propose_workflow,
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
        from src.domain.agents.guardrails import AgentProfileGuardrail

        agent_data = spec or kwargs
        if "spec" in agent_data and isinstance(agent_data["spec"], dict):
            agent_data = agent_data["spec"]

        available_tools = None
        if self.tool_registry:
            available_tools = {t.name for t in self.tool_registry.list_tools()}

        profile = AgentProfileGuardrail.validate(agent_data, available_tools=available_tools)

        self.agent_registry.register_custom_agent(profile)
        return {
            "status": "created",
            "id": profile.id,
            "name": profile.name,
            "purpose": profile.purpose.value,
        }

    def _draft_kwargs(self, **kwargs: Any) -> Dict[str, Any]:
        from src.application.kernel.tool_registry import get_tool_context

        ctx = get_tool_context()
        session_id = str(ctx.get("session_id") or "").strip()
        agent_id = str(ctx.get("agent_id") or "").strip() or "assistant"
        job_id = str(ctx.get("job_id") or "").strip() or None
        return {
            "store": self.store,
            "data_dir": self._resolved_data_dir(),
            "session_id": session_id,
            "agent_id": agent_id,
            "requested_by_job_id": job_id,
            "agent_registry": self.agent_registry,
            **kwargs,
        }

    async def propose_skill(
        self,
        what: str,
        why: str,
        how: str,
        where: str,
        pack_id: Optional[str] = None,
        prefer_existing_agent_id: Optional[str] = None,
        new_agent_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Park a skill-pack HITL draft. Does not write SKILL.md [REQ-BUILD-001]."""
        from src.application.orchestration.skill_proposals import propose_skill as park

        try:
            return park(
                **self._draft_kwargs(
                    what=what,
                    why=why,
                    how=how,
                    where=where,
                    pack_id=pack_id,
                    prefer_existing_agent_id=prefer_existing_agent_id,
                    new_agent_id=new_agent_id,
                )
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc), "disk_written": False, "status": None}

    async def propose_tool(
        self,
        what: str,
        why: str,
        how: str,
        where: str,
        pack_id: str,
        tool_json: Any,
        prefer_existing_agent_id: Optional[str] = None,
        new_agent_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Park a tool HITL draft. Does not write Python [REQ-BUILD-002]."""
        from src.application.orchestration.skill_proposals import propose_tool as park

        try:
            return park(
                **self._draft_kwargs(
                    what=what,
                    why=why,
                    how=how,
                    where=where,
                    pack_id=pack_id,
                    tool_json=tool_json,
                    prefer_existing_agent_id=prefer_existing_agent_id,
                    new_agent_id=new_agent_id,
                )
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc), "disk_written": False, "status": None}

    async def propose_workflow(
        self,
        what: str,
        why: str,
        how: str,
        where: str,
        pack_id: Optional[str] = None,
        prefer_existing_agent_id: Optional[str] = None,
        new_agent_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Park a playbook SOP workflow HITL draft. No Job auto-run [REQ-BUILD-003]."""
        from src.application.orchestration.skill_proposals import propose_workflow as park

        try:
            return park(
                **self._draft_kwargs(
                    what=what,
                    why=why,
                    how=how,
                    where=where,
                    pack_id=pack_id,
                    prefer_existing_agent_id=prefer_existing_agent_id,
                    new_agent_id=new_agent_id,
                )
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc), "disk_written": False, "status": None}
