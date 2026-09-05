"""
Scoped Tool Registry with Role-Based Access Control (RBAC) [REQ-KERNEL-002].
"""

import asyncio
import inspect
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile, ToolResult

_tool_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "autoreiv_tool_context", default=None
)


def get_tool_context() -> Dict[str, Any]:
    """Caller agent id and session for the in-flight tool execution."""
    return dict(_tool_context.get() or {})


@dataclass
class ToolRegistration:
    definition: ToolDefinition
    handler: Callable[..., Any]


class ScopedToolRegistry:
    """
    Registry for tools and functions with per-agent RBAC enforcement.
    """

    def __init__(self):
        self._tools: Dict[str, ToolRegistration] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Register a tool handler function."""
        definition = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
        )
        self._tools[name] = ToolRegistration(definition=definition, handler=handler)

    def mount_mcp_tool(
        self,
        definition: ToolDefinition,
        handler: Callable[..., Any],
    ) -> None:
        """Mount an external MCP tool definition and dispatch handler [REQ-MCP-002]."""
        self._tools[definition.name] = ToolRegistration(definition=definition, handler=handler)

    def unmount_tool(self, name: str) -> bool:
        """Remove a tool registration from the registry."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get the ToolDefinition for a given tool name."""
        reg = self._tools.get(name)
        return reg.definition if reg else None

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tool definitions."""
        return [reg.definition for reg in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        """Check whether a tool name is registered."""
        return name in self._tools

    def get_tools_for_agent(self, agent: AgentProfile) -> List[ToolDefinition]:
        """
        Return only the tool definitions that the given agent is authorized to use.
        """
        allowed = set(agent.allowed_tool_names)
        if getattr(agent, "storage_enabled", False):
            allowed.add("query_agent_database")
            allowed.add("execute_agent_database")
        if "read_document_file" in self._tools:
            allowed.add("read_document_file")
        return [reg.definition for name, reg in self._tools.items() if name in allowed]

    async def execute(
        self,
        tool_call: ToolCall,
        agent: AgentProfile,
        session_id: Optional[str] = None,
        approval_mode: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a tool call after verifying RBAC permissions against the agent profile.
        """
        mode = "run" if str(approval_mode or "").strip().lower() == "run" else "ask"
        token = _tool_context.set(
            {
                "agent_id": agent.id,
                "session_id": session_id,
                "approval_mode": mode,
                "job_id": job_id,
                "allowed_skill": list(getattr(agent, "allowed_skill", None) or []),
            }
        )
        try:
            return await self._execute_inner(tool_call, agent)
        finally:
            _tool_context.reset(token)

    async def _execute_inner(self, tool_call: ToolCall, agent: AgentProfile) -> ToolResult:
        start_time = time.perf_counter()

        # 1. Verify RBAC authorization
        allowed = set(agent.allowed_tool_names)
        if getattr(agent, "storage_enabled", False):
            allowed.add("query_agent_database")
            allowed.add("execute_agent_database")
        if "read_document_file" in self._tools:
            allowed.add("read_document_file")
        if tool_call.name not in allowed:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"Tool '{tool_call.name}' is not authorized for agent '{agent.id}'.",
                duration_ms=elapsed_ms,
            )

        # 2. Verify tool existence
        registration = self._tools.get(tool_call.name)
        if not registration:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"Tool '{tool_call.name}' not found in system registry.",
                duration_ms=elapsed_ms,
            )

        # 3. Execute tool handler
        try:
            handler = registration.handler
            args = tool_call.arguments or {}

            if inspect.iscoroutinefunction(handler):
                output = await handler(**args)
            elif callable(handler):
                # Run sync handler in default executor to avoid blocking event loop
                output = await asyncio.to_thread(handler, **args)
            else:
                raise TypeError(f"Tool handler for '{tool_call.name}' is not callable.")

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=output,
                success=True,
                error=None,
                duration_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=str(e),
                duration_ms=elapsed_ms,
            )
