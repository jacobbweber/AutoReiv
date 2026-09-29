"""inspect_agent: read an agent's identity, ticked skills and resolved tools [CARD-569].

Read-only. Used by the agent-authoring skill to see what an agent already has before
proposing something new. The agent builder tools are gone.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.application.agent_skills.allowed_tools import resolve_allowed_tools, ticked_skills
from src.application.kernel.tool_registry import ScopedToolRegistry

INSPECT_AGENT = "inspect_agent"


class AgentInspectTools:
    """Registers the read-only inspect_agent tool."""

    def __init__(self, agent_registry: Any) -> None:
        self.agent_registry = agent_registry

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name=INSPECT_AGENT,
            description=(
                "Read an agent's name, description, ticked skills and resolved tools without changing it. "
                "Use it to see what the agent already does before proposing a new skill or tool."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent id (e.g. autoreiv, developer, tutor, architect, direct).",
                    },
                },
                "required": ["agent_id"],
            },
            handler=self.inspect_agent,
        )

    def _profile(self, agent_id: str) -> Optional[Any]:
        registry = self.agent_registry
        if registry is None:
            return None
        getter = getattr(registry, "get_agent", None) or getattr(registry, "get_profile", None)
        return getter(agent_id) if getter else None

    async def inspect_agent(self, agent_id: str, **kwargs: Any) -> Dict[str, Any]:
        clean_id = str(agent_id or "").strip()
        if not clean_id:
            return {"success": False, "error": "agent_id is required."}
        profile = self._profile(clean_id)
        if profile is None:
            return {"success": False, "error": f"Agent '{clean_id}' not found."}
        return {
            "success": True,
            "agent_id": clean_id,
            "name": getattr(profile, "name", clean_id),
            "description": getattr(profile, "description", "") or "",
            "skills": ticked_skills(profile),
            "tools": sorted(resolve_allowed_tools(profile)),
        }
