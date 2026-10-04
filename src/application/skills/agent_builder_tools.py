"""
Agent Builder Tools [REQ-FORGE-005] [REQ-BUILD-001 - REQ-BUILD-014].
Equips Developer with meta-tooling to inspect system capabilities and park
HITL drafts for skills and tools. New agents are created in Agent Studio [CARD-569].
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentTone
from src.domain.settings.models import ModelPurpose
from src.infrastructure.agents.registry import BuiltinAgentRegistry

# CARD-527: keep the authoring catalog under the 8 KB payload-bloat line by default (it was 20,146 bytes).
CATALOG_BYTE_BUDGET = 7500
_CATALOG_DEFAULT_LIMIT = 30
_CATALOG_MAX_LIMIT = 200
_CATALOG_DESCRIPTION_CHARS = 90


def _short(text: Any, size: int = _CATALOG_DESCRIPTION_CHARS) -> str:
    clean = " ".join(str(text or "").split())
    return clean if len(clean) <= size else clean[: size - 3].rstrip() + "..."


def _matches(query: str, *fields: Any) -> bool:
    return not query or any(query in str(f or "").lower() for f in fields)


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
            description=(
                "Authoring catalog: platform tools, skills, purposes and tones. Pass query to find a tool or skill "
                "by name or words in its description; results are paged (limit, offset) and stay under 8 KB."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Words to match in tool/skill names or descriptions."},
                    "limit": {
                        "type": "integer",
                        "description": f"Max tools and max skills per page (default {_CATALOG_DEFAULT_LIMIT}).",
                    },
                    "offset": {"type": "integer", "description": "Skip this many tools and skills (paging)."},
                },
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

    async def list_available_skills_and_tools(
        self, query: str = "", limit: Optional[int] = None, offset: int = 0, **kwargs
    ) -> Dict[str, Any]:
        """Authoring catalog: skills, platform tools, purposes and tones. Not a tool list for the caller.

        CARD-527: filtered by ``query``, paged by ``limit``/``offset``, descriptions shortened, and trimmed
        to stay under 8 KB; the counts say how many matched so the caller can page or narrow.
        """
        from src.application.kernel.tool_registry import get_tool_context
        from src.infrastructure.content.store import get_store

        needle = str(query or "").strip().lower()
        try:
            size = max(1, min(int(limit or _CATALOG_DEFAULT_LIMIT), _CATALOG_MAX_LIMIT))
        except (TypeError, ValueError):
            size = _CATALOG_DEFAULT_LIMIT
        try:
            start = max(0, int(offset or 0))
        except (TypeError, ValueError):
            start = 0
        offered = get_tool_context().get("offered_tools")
        callable_now = set(offered or [])
        all_tools: List[Dict[str, Any]] = []
        if self.tool_registry:
            for t in self.tool_registry.list_tools():
                if not _matches(needle, t.name, t.description):
                    continue
                row: Dict[str, Any] = {"name": t.name, "description": _short(t.description)}
                if offered is not None:  # CARD-607: mark the few the caller can call on this turn
                    row["you_can_call"] = t.name in callable_now
                all_tools.append(row)
        all_skills = [
            {"id": f.id, "name": f.meta.get("name") or f.id, "description": _short(f.meta.get("description"))}
            for f in get_store().skills.list()
            if _matches(needle, f.id, f.meta.get("name"), f.meta.get("description"))
        ]
        tools_list = all_tools[start : start + size]
        skills = all_skills[start : start + size]

        purposes = [p.value for p in ModelPurpose]
        tones = [t.value for t in AgentTone]

        result = {
            "note": (
                "Authoring catalog only: use it to check whether a tool already exists. These tools are not "
                "callable by you unless you_can_call is true; any other call is refused. Agents get tools by "
                "ticking skills; propose a skill (or attaching a tool to one) for Jacob to accept."
            ),
            "query": needle,
            "total_tools": len(all_tools),
            "total_skills": len(all_skills),
            "offset": start,
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
        # Still over budget (long names): drop rows from the end of the longer list until it fits.
        while (tools_list or skills) and len(json.dumps(result, default=str)) > CATALOG_BYTE_BUDGET:
            (tools_list if len(tools_list) >= len(skills) else skills).pop()
        # One offset pages both lists: advance by the shorter page among lists that still have rows left,
        # so nothing is skipped (the other list may repeat a few rows).
        unfinished = [
            len(page) for page, rows in ((tools_list, all_tools), (skills, all_skills)) if start + len(page) < len(rows)
        ]
        next_offset = start + max(1, min(unfinished)) if unfinished else None
        result["next_offset"] = next_offset
        if next_offset is not None:
            result["more"] = (
                f"Showing {len(tools_list)} of {len(all_tools)} tools and {len(skills)} of {len(all_skills)} "
                f"skills. Pass query to narrow, or offset={next_offset} for the next page."
            )
        return result


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

