"""
Scoped Tool Registry with Role-Based Access Control (RBAC) [REQ-KERNEL-002].
"""

import asyncio
import inspect
import os
import re
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

    def __init__(self, state_store: Optional[Any] = None):
        self.state_store = state_store
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
        """Mount an external MCP tool definition and dispatch handler [REQ-MCP-002].

        Mount/list is not authorization [CARD-225]: callers must still pass
        ToolPolicyGate + matched capability subset before execute.
        """
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
        for srv in getattr(agent, "mcp_servers", []) or []:
            srv_name = srv.name if hasattr(srv, "name") else (srv.get("name") if isinstance(srv, dict) else "")
            if srv_name:
                for reg_name in self._tools:
                    if reg_name.startswith(f"mcp_{srv_name}_"):
                        allowed.add(reg_name)
        if getattr(agent, "storage_enabled", False):
            allowed.add("query_agent_database")
            allowed.add("execute_agent_database")
        if "read_document_file" in self._tools:
            allowed.add("read_document_file")
        if getattr(agent, "allow_wiki_access", True) is False:
            allowed = {t for t in allowed if not (t.startswith("wiki_") or "wiki" in t.lower())}
        return [reg.definition for name, reg in self._tools.items() if name in allowed]

    async def execute(
        self,
        tool_call: ToolCall,
        agent: AgentProfile,
        session_id: Optional[str] = None,
        approval_mode: Optional[str] = None,
        job_id: Optional[str] = None,
        state_store: Optional[Any] = None,
    ) -> ToolResult:
        """
        Execute a tool call after verifying RBAC permissions against the agent profile.
        """
        if getattr(agent, "allow_wiki_access", True) is False:
            if tool_call.name.startswith("wiki_") or "wiki" in tool_call.name.lower():
                return ToolResult(
                    call_id=tool_call.id,
                    tool_name=tool_call.name,
                    output=None,
                    success=False,
                    error=f"Permission denied: Agent '{agent.id}' does not have Wiki access enabled [CARD-173].",
                    duration_ms=0.0,
                )

        mode = "run" if str(approval_mode or "").strip().lower() == "run" else "ask"
        store = state_store or self.state_store
        resolved_creds: Dict[str, str] = {}
        env_vars_set: List[str] = []
        if store and getattr(agent, "allowed_credentials", None):
            for cid in agent.allowed_credentials:
                try:
                    cred = store.get_credential(cid)
                    if cred and cred.secret:
                        resolved_creds[cid] = cred.secret
                        env_key = f"AUTOREIV_CRED_{re.sub(r'[^A-Za-z0-9_]', '_', cid).upper()}"
                        if env_key not in os.environ:
                            os.environ[env_key] = cred.secret
                            env_vars_set.append(env_key)
                except Exception:
                    pass

        token = _tool_context.set(
            {
                "agent_id": agent.id,
                "session_id": session_id,
                "approval_mode": mode,
                "job_id": job_id,
                "allowed_skill": list(getattr(agent, "allowed_skill", None) or []),
                "credentials": resolved_creds,
            }
        )
        try:
            return await self._execute_inner(tool_call, agent)
        finally:
            for k in env_vars_set:
                os.environ.pop(k, None)
            _tool_context.reset(token)

    async def _execute_inner(self, tool_call: ToolCall, agent: AgentProfile) -> ToolResult:
        start_time = time.perf_counter()

        # 1. Verify RBAC authorization
        allowed = set(agent.allowed_tool_names)
        for srv in getattr(agent, "mcp_servers", []) or []:
            srv_name = srv.name if hasattr(srv, "name") else (srv.get("name") if isinstance(srv, dict) else "")
            if srv_name:
                for reg_name in self._tools:
                    if reg_name.startswith(f"mcp_{srv_name}_"):
                        allowed.add(reg_name)
        if getattr(agent, "storage_enabled", False):
            allowed.add("query_agent_database")
            allowed.add("execute_agent_database")
        if "read_document_file" in self._tools:
            allowed.add("read_document_file")

        # Flexible matching for MCP tools (bare name vs scoped name)
        target_name = tool_call.name
        if target_name not in allowed:
            matched = False
            for a in allowed:
                if (a.startswith("mcp_") and a.endswith(f"_{target_name}")) or (target_name.startswith("mcp_") and target_name.endswith(f"_{a}")):
                    matched = True
                    break
            if not matched:
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
        registration = self._tools.get(target_name)
        if not registration:
            for t_name, reg in self._tools.items():
                if t_name.startswith("mcp_") and t_name.endswith(f"_{target_name}"):
                    registration = reg
                    break
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
                if inspect.iscoroutine(output):
                    output = await output
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
