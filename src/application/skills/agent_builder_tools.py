"""
Agent Builder Tools [REQ-FORGE-005] [REQ-BUILD-001 - REQ-BUILD-014].
Equips Developer with meta-tooling to inspect system capabilities and park
HITL drafts for skills and tools. New agents are created in Agent Studio [CARD-569].
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentTone
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry


class AgentBuilderTools:
    """
    Tool group providing agent introspection, specification drafts, and HITL skill drafts.
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

        payload_fields = {
            "what": {"type": "string", "description": "What is being proposed (skill, tool, or playbook SOP)."},
            "why": {"type": "string", "description": "Why this is needed."},
            "how": {
                "type": "string",
                "description": "How it should work (playbook SOP / JSON stub). Never a Python builtin write.",
            },
            "where": {
                "type": "string",
                "description": "Destination path relative to $DATA_DIR (typically skills/<slug>/SKILL.md).",
            },
            "skill_id": {"type": "string", "description": "Target skill id (directory slug under $DATA_DIR/skills)."},
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
                "Recommend-capability only: park a HITL draft for a new skill when no existing runbook fits. "
                "Not agent creation. Creates a proposals row status draft. Does not write SKILL.md until commit after Approve."
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
                "Recommend-capability only: park a HITL draft for a declared tool (JSON stub) when no catalog tool fits. "
                "Not agent creation. Do not call this to create a named agent with existing tools. "
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
                "required": ["what", "why", "how", "where", "skill_id", "tool_json"],
            },
            handler=self.propose_tool,
        )

        registry.register_tool(
            name="commit_skill",
            description=(
                "Write an approved skill/tool proposal to $DATA_DIR/skills via UserSkillCatalog. "
                "Requires HITL status=approved. Draft/rejected fail closed. Soft sprawl warning is not a block. "
                "Never writes Python under src/."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "Approved proposals.id to commit."},
                    "overwrite": {
                        "type": "boolean",
                        "description": "Replace an existing SKILL.md playbook (skill kind only). Default false.",
                    },
                },
                "required": ["proposal_id"],
            },
            handler=self.commit_skill,
        )

    async def list_available_skills_and_tools(self, **kwargs) -> Dict[str, Any]:
        """Authoring catalog: skills, platform tools, purposes and tones. Not a tool list for the caller."""
        from src.application.kernel.tool_registry import get_tool_context
        from src.infrastructure.content.store import get_store

        offered = get_tool_context().get("offered_tools")
        callable_now = set(offered or [])
        tools_list = []
        if self.tool_registry:
            for t in self.tool_registry.list_tools():
                row = {"name": t.name, "description": t.description}
                if offered is not None:  # CARD-607: mark the few the caller can call on this turn
                    row["you_can_call"] = t.name in callable_now
                tools_list.append(row)
        skills = [
            {"id": f.id, "name": f.meta.get("name") or f.id, "description": f.meta.get("description") or ""}
            for f in get_store().skills.list()
        ]

        purposes = [p.value for p in ModelPurpose]
        tones = [t.value for t in AgentTone]

        return {
            "note": (
                "Authoring catalog only: use it to check whether a tool already exists. These tools are not "
                "callable by you unless you_can_call is true; any other call is refused. Agents get tools by "
                "ticking skills; propose a skill (or attaching a tool to one) for Jacob to accept."
            ),
            "skills": skills,
            "catalog_tools": tools_list,
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


    def _draft_kwargs(self, **kwargs: Any) -> Dict[str, Any]:
        from src.application.kernel.tool_registry import get_tool_context

        ctx = get_tool_context()
        session_id = str(ctx.get("session_id") or "").strip()
        agent_id = str(ctx.get("agent_id") or "").strip() or "autoreiv"
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
        skill_id: Optional[str] = None,
        prefer_existing_agent_id: Optional[str] = None,
        new_agent_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Park a skill HITL draft. Does not write SKILL.md [REQ-BUILD-001]."""
        from src.application.orchestration.skill_proposals import propose_skill as park

        try:
            return park(
                **self._draft_kwargs(
                    what=what,
                    why=why,
                    how=how,
                    where=where,
                    skill_id=skill_id,
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
        skill_id: str,
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
                    skill_id=skill_id,
                    tool_json=tool_json,
                    prefer_existing_agent_id=prefer_existing_agent_id,
                    new_agent_id=new_agent_id,
                )
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc), "disk_written": False, "status": None}

    def _catalog(self):
        from src.application.skills.user_catalog import UserSkillCatalog

        return UserSkillCatalog(skills_dir=self._resolved_data_dir() / "skills")

    async def commit_skill(
        self,
        proposal_id: str,
        overwrite: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """Write an approved skill via UserSkillCatalog [REQ-BUILD-012]."""
        from src.application.kernel.tool_registry import get_tool_context
        from src.application.orchestration.skill_proposals import commit_skill as apply_commit

        ctx = get_tool_context()
        try:
            return apply_commit(
                self.store,
                proposal_id=proposal_id,
                data_dir=self._resolved_data_dir(),
                catalog=self._catalog(),
                agent_registry=self.agent_registry,
                overwrite=bool(overwrite),
                approval_mode=ctx.get("approval_mode"),
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc), "disk_written": False, "src_written": False}

