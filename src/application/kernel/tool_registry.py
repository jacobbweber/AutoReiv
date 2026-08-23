"""
Scoped Tool Registry with Role-Based Access Control (RBAC) [REQ-KERNEL-002].
"""

import asyncio
import inspect
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile, ToolResult


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

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get the ToolDefinition for a given tool name."""
        reg = self._tools.get(name)
        return reg.definition if reg else None

    def get_tools_for_agent(self, agent: AgentProfile) -> List[ToolDefinition]:
        """
        Return only the tool definitions that the given agent is authorized to use.
        """
        allowed = set(agent.allowed_tool_names)
        return [reg.definition for name, reg in self._tools.items() if name in allowed]

    async def execute(self, tool_call: ToolCall, agent: AgentProfile) -> ToolResult:
        """
        Execute a tool call after verifying RBAC permissions against the agent profile.
        """
        start_time = time.perf_counter()

        # 1. Verify RBAC authorization
        if tool_call.name not in agent.allowed_tool_names:
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
