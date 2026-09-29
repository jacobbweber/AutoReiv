"""
Platform Primitive Tools [CARD-339, ADR-0052].
Lean baseline primitives mounted on all standard turns:
- ask_clarification(question: str)
- get_session_info()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context

logger = logging.getLogger(__name__)


class PlatformPrimitiveTools:
    """Platform primitive callable handlers."""

    def __init__(self, state_store: Optional[Any] = None, tool_registry: Optional[ScopedToolRegistry] = None) -> None:
        self.state_store = state_store
        self.tool_registry = tool_registry

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
