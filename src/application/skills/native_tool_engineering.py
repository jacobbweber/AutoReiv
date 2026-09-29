"""Toolsmith tools for the native custom-tool lane [CARD-423, CARD-571].

Same service as POST /api/tools/native. No second registration store.
"""

from __future__ import annotations

from typing import Any, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.tools.native_packaging import NativeCustomToolService, NativeToolCheckFailed


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

    async def register_native_tool(
        self,
        name: str,
        description: str,
        code: str,
        parameters: Optional[dict] = None,
        requires_hitl: bool = True,
        risk_level: str = "medium",
        target_agent_id: Optional[str] = None,
        target_skill_id: Optional[str] = None,
        sample_arguments: Optional[dict] = None,
    ) -> dict[str, Any]:
        """Register one native AutoReiv tool after one sandbox run [CARD-511]. Does not attach an MCP server."""
        try:
            return await self._service().register(
                {
                    "name": name,
                    "description": description,
                    "code": code,
                    "parameters": parameters or {},
                    "requires_hitl": requires_hitl,
                    "risk_level": risk_level,
                    "target_agent_id": target_agent_id or "",
                    "target_skill_id": target_skill_id or "",
                    "sample_arguments": sample_arguments,
                }
            )
        except NativeToolCheckFailed as exc:
            # Relay this to the operator, fix the tool, and call register again.
            return {
                "success": False,
                "registered": False,
                "name": name,
                "message": str(exc),
                "check": exc.check,
            }

    def view_native_tool(self, name: str) -> dict[str, Any]:
        """Read-only: code, check result and approval state of one runtime-built tool [CARD-571 D6]."""
        from src.application.tools.native_packaging import NativeToolError

        try:
            return self._service().view(name)
        except NativeToolError as exc:
            return {"success": False, "name": name, "message": str(exc)}

    def plan_native_folder(self, directory: str) -> dict[str, Any]:
        """Plan one tool per script in a directory. Does not register or open a folder picker."""
        return self._service().plan_folder(directory)

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        self.tool_registry = registry
        registry.register_tool(
            name="register_native_tool",
            description=(
                "Save a native AutoReiv custom tool (no MCP server). It is saved disabled: only Jacob enables it "
                "in Tools Studio, after reading the code. "
                "Code must define run(**kwargs). requires_hitl defaults to true. "
                "Pass target_agent_id for the agent that needs it: this creates a pending proposal to attach the "
                "tool to a skill of that agent (target_skill_id, or a new skill); the agent can use it only after "
                "Jacob accepts. "
                "Saving runs the tool check first (import plus one sample call in a temporary folder; this is "
                "not isolation: network and file access are allowed and shown to Jacob as a warning); "
                "a result starting 'Not registered:' means nothing was saved: tell the operator, fix the code, call again."
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
                    "target_agent_id": {
                        "type": "string",
                        "description": "Agent that needs the tool. Creates a pending attach-tool-to-skill proposal.",
                    },
                    "target_skill_id": {
                        "type": "string",
                        "description": "Existing skill of that agent to attach to. Omit to propose a new skill.",
                    },
                    "sample_arguments": {
                        "type": "object",
                        "description": "Harmless input for the one check call. Omit to build it from parameters.",
                    },
                },
                "required": ["name", "description", "code"],
            },
            handler=self.register_native_tool,
        )
        registry.register_tool(
            name="view_native_tool",
            description=(
                "Read one runtime-built tool: its code, description, parameters, last check and approval state "
                "(enabled, disabled or needs_reapproval). Read-only. Use it before changing an existing tool; "
                "register_native_tool with the same name saves new code, which Jacob must approve again."
            ),
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Runtime tool id."}},
                "required": ["name"],
            },
            handler=self.view_native_tool,
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
