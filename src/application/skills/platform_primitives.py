"""
Platform Primitive Tools [CARD-339, ADR-0052].
Lean baseline primitives mounted on all standard turns:
- activate_skill(skills: list[str])
- ask_clarification(question: str)
- get_session_info()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context

logger = logging.getLogger(__name__)


class PlatformPrimitiveTools:
    """Platform primitive callable handlers."""

    def __init__(self, state_store: Optional[Any] = None, tool_registry: Optional[ScopedToolRegistry] = None) -> None:
        self.state_store = state_store
        self.tool_registry = tool_registry

    def activate_skill(self, skills: List[str]) -> Dict[str, Any]:
        """
        Load the tools of one or more skills ticked for this agent for the current turn.
        Skills that are not ticked are refused and mount nothing (CARD-539, ADR-0061).
        """
        from src.application.agent_skills.allowed_tools import skill_tools

        ctx = get_tool_context() or {}
        agent_id = ctx.get("agent_id")
        ticks = {str(s).strip().lower(): str(s).strip() for s in ctx.get("allowed_skill") or [] if str(s).strip()}
        requested = [str(s).strip() for s in skills or [] if str(s).strip()]
        valid = [ticks[s.lower()] for s in requested if s.lower() in ticks]
        refused = [s for s in requested if s.lower() not in ticks]
        bound = skill_tools(valid, agent_id)
        names = [t.name for t in self.tool_registry.list_tools()] if self.tool_registry is not None else []
        activated_tools = list(
            dict.fromkeys(
                n
                for sid in valid
                for t in bound.get(sid) or []
                for n in ([x for x in names if x.startswith(t[:-1])] if t.endswith("*") else [t])
            )
        )

        parts = []
        if valid:
            parts.append(f"Activated skills: {', '.join(valid)}. Tools available for subsequent steps: {', '.join(activated_tools)}.")
        if refused:
            parts.append(
                f"These skills are not ticked for this agent: {', '.join(refused)}. Nothing was loaded for them; "
                "hand off to an agent that has the skill, or suggest Ask Developer."
            )
        return {
            "status": "activated" if valid else "refused",
            "activated_skills": valid,
            "activated_tools": activated_tools,
            "refused_skills": refused,
            "session_id": ctx.get("session_id"),
            "agent_id": agent_id,
            "message": " ".join(parts) or "No skills named.",
        }

    def ask_clarification(self, question: str) -> Dict[str, Any]:
        """
        Ask the human operator a clarifying question when requirements or constraints are underspecified.
        """
        ctx = get_tool_context() or {}
        return {
            "status": "clarification_requested",
            "question": str(question).strip(),
            "session_id": ctx.get("session_id"),
            "agent_id": ctx.get("agent_id"),
        }

    def get_session_info(self) -> Dict[str, Any]:
        """
        Retrieve metadata about the current session, active agent, and operating context.
        """
        ctx = get_tool_context() or {}
        session_id = ctx.get("session_id")
        agent_id = ctx.get("agent_id", "autoreiv")
        job_id = ctx.get("job_id")

        info: Dict[str, Any] = {
            "session_id": session_id,
            "agent_id": agent_id,
            "job_id": job_id,
            "approval_mode": ctx.get("approval_mode", "ask"),
            "status": "active",
        }
        if self.state_store and session_id:
            try:
                sess = self.state_store.get_session(session_id)
                if sess:
                    # ISO strings only — raw datetime broke Tutor chat JSON (CARD-437/438).
                    for key in ("created_at", "updated_at"):
                        raw = getattr(sess, key, None)
                        if raw is None:
                            continue
                        if hasattr(raw, "isoformat"):
                            try:
                                info[key] = raw.isoformat()
                                continue
                            except Exception:
                                pass
                        info[key] = str(raw)
            except Exception:
                pass
        return info

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register the platform primitives into the ScopedToolRegistry."""
        self.tool_registry = registry
        registry.register_tool(
            name="activate_skill",
            description="Load the tools of skills ticked for you (listed under Your domain) for the current turn. Unticked skills are refused.",
            parameters={
                "type": "object",
                "properties": {
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of platform skill names to activate, e.g. ['wiki'] or ['diagnostics'].",
                    },
                },
                "required": ["skills"],
            },
            handler=self.activate_skill,
        )

        registry.register_tool(
            name="ask_clarification",
            description="Ask the operator a clarifying question when intent, scope, or parameters are ambiguous.",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question to ask the operator.",
                    },
                },
                "required": ["question"],
            },
            handler=self.ask_clarification,
        )

        registry.register_tool(
            name="get_session_info",
            description="Retrieve operating context, session ID, and active agent metadata.",
            parameters={
                "type": "object",
                "properties": {},
            },
            handler=self.get_session_info,
        )
