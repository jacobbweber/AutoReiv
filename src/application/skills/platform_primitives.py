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

    def __init__(self, state_store: Optional[Any] = None) -> None:
        self.state_store = state_store

    def activate_skill(self, skills: List[str]) -> Dict[str, Any]:
        """
        Dynamically activate one or more platform skills (e.g. 'wiki', 'diagnostics', 'tasks', 'coding')
        to mount their specialized tools and procedural runbooks for the current turn.
        """
        from src.application.agent_packs.schema import PLATFORM_SKILL_TOOLS

        normalized = [str(s).strip().lower() for s in skills if str(s).strip()]
        valid_skills: List[str] = []
        unknown_skills: List[str] = []
        activated_tools: List[str] = []

        for s in normalized:
            if s in PLATFORM_SKILL_TOOLS:
                valid_skills.append(s)
                activated_tools.extend(PLATFORM_SKILL_TOOLS[s])
            else:
                unknown_skills.append(s)

        ctx = get_tool_context() or {}
        session_id = ctx.get("session_id")
        agent_id = ctx.get("agent_id")

        return {
            "status": "activated" if valid_skills else "failed",
            "activated_skills": valid_skills,
            "activated_tools": activated_tools,
            "unknown_skills": unknown_skills,
            "session_id": session_id,
            "agent_id": agent_id,
            "message": (
                f"Activated skills: {', '.join(valid_skills)}. "
                f"Tools available for subsequent steps: {', '.join(activated_tools)}."
                if valid_skills
                else f"No valid platform skills found matching: {unknown_skills}"
            ),
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
                    info["created_at"] = getattr(sess, "created_at", None)
                    info["updated_at"] = getattr(sess, "updated_at", None)
            except Exception:
                pass
        return info

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register the platform primitives into the ScopedToolRegistry."""
        registry.register_tool(
            name="activate_skill",
            description="Dynamically activate platform skills (e.g. 'wiki', 'diagnostics', 'tasks', 'coding') to unlock their specialized tool sets and SOP runbooks for the current turn.",
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
