"""Developer tools for the native custom-tool lane [CARD-423].

Same service as POST /api/tools/native. No second registration store.
"""

from __future__ import annotations

from typing import Any, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.tools.native_packaging import NativeCustomToolService


class NativeToolEngineeringTools:
    def __init__(
        self,
        state_store: Optional[Any] = None,
        tool_registry: Optional[ScopedToolRegistry] = None,
        agent_registry: Optional[Any] = None,
    ) -> None:
        self.state_store = state_store
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.service: Optional[NativeCustomToolService] = None

    def _service(self) -> NativeCustomToolService:
        if self.service is not None:
            return self.service
        self.service = NativeCustomToolService(
            store=self.state_store,
            tool_registry=self.tool_registry,
            agent_registry=self.agent_registry,
        )
        return self.service

    def register_native_tool(
        self,
        name: str,
        description: str,
        code: str,
        parameters: Optional[dict] = None,
        requires_hitl: bool = True,
        risk_level: str = "medium",
        grant_agent_ids: Optional[list] = None,
    ) -> dict[str, Any]:
        """Register one native AutoReiv tool. Does not attach an MCP server."""
        return self._service().register(
            {
                "name": name,
                "description": description,
                "code": code,
                "parameters": parameters or {},
                "requires_hitl": requires_hitl,
                "risk_level": risk_level,
                "grant_agent_ids": grant_agent_ids or [],
            }
        )

    def plan_native_folder(self, directory: str) -> dict[str, Any]:
        """Plan one tool per script in a directory. Does not register or open a folder picker."""
        return self._service().plan_folder(directory)

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        self.tool_registry = registry
        registry.register_tool(
            name="register_native_tool",
            description=(
                "Register a native AutoReiv custom tool that runs in the sandbox without an MCP server. "
                "Code must define run(**kwargs). requires_hitl defaults to true. "
                "Pass grant_agent_ids for agents allowed to call it."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Lowercase tool id, not an mcp_ name."},
                    "description": {"type": "string", "description": "What the operator sees in the catalog."},
                    "code": {
                        "type": "string",
                        "description": "Python source that defines run(**kwargs) and returns a JSON-friendly value.",
                    },
                    "parameters": {"type": "object", "description": "JSON Schema for the tool arguments."},
                    "requires_hitl": {
                        "type": "boolean",
                        "description": "When true (default), ToolPolicyGate parks the call until the operator runs it.",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "high always requires HITL.",
                    },
                    "grant_agent_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Agent ids to add this tool onto, using the existing agent allowlist.",
                    },
                },
                "required": ["name", "description", "code"],
            },
            handler=self.register_native_tool,
        )
        registry.register_tool(
            name="plan_native_folder",
            description=(
                "Given a filesystem path from developer chat, list one suggested tool per script. "
                "Does not register tools and does not open a Tools Studio folder picker."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory path supplied in conversation."},
                },
                "required": ["directory"],
            },
            handler=self.plan_native_folder,
        )
