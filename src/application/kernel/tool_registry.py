"""
Scoped Tool Registry with Role-Based Access Control (RBAC) [REQ-KERNEL-002].
"""

import asyncio
import inspect
import json
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Collection, Dict, List, Optional

from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile, ToolResult

_tool_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "autoreiv_tool_context", default=None
)


def get_tool_context() -> Dict[str, Any]:
    """Caller agent id and session for the in-flight tool execution."""
    return dict(_tool_context.get() or {})


CREDENTIAL_ENV_PREFIX = "AUTOREIV_CRED_"


def credential_env_key(credential_id: str) -> str:
    """Environment name a subprocess tool sees for one credential: AUTOREIV_CRED_<ID>."""
    return f"{CREDENTIAL_ENV_PREFIX}{re.sub(r'[^A-Za-z0-9_]', '_', credential_id).upper()}"


def credential_env_from_context() -> Dict[str, str]:
    """CARD-519: the calling agent's own credentials as env overrides for one subprocess (never os.environ)."""
    creds = (_tool_context.get() or {}).get("credentials") or {}
    return {credential_env_key(cid): secret for cid, secret in creds.items() if secret}


def unwrap_raw_arguments(handler: Any, args: Dict[str, Any]) -> Dict[str, Any]:
    """CARD-523: {"raw": "{...}"} (the model's JSON arguments wrapped as one string) becomes the real arguments."""
    if not isinstance(args, dict) or set(args) != {"raw"} or not isinstance(args.get("raw"), str):
        return args
    try:
        if "raw" in inspect.signature(handler).parameters:
            return args
    except (TypeError, ValueError):
        return args
    try:
        parsed = json.loads(args["raw"])
    except ValueError:
        return args
    return parsed if isinstance(parsed, dict) else args


def argument_mismatch_error(tool_name: str, handler: Any, schema: Optional[Dict[str, Any]], args: Dict[str, Any]) -> Optional[str]:
    """CARD-562: unknown or missing arguments become a clear tool error listing the accepted parameters.

    Unknown arguments are never dropped silently (that can lose data); the model is told to call again.
    """
    try:
        sig = inspect.signature(handler)
    except (TypeError, ValueError):
        return None
    try:
        sig.bind(**args)
        return None
    except TypeError:
        pass
    params = sig.parameters
    takes_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    named = {n for n, p in params.items() if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)}
    unknown = [] if takes_kwargs else sorted(k for k in args if k not in named)
    missing = [
        n for n, p in params.items()
        if p.default is inspect.Parameter.empty
        and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        and n not in args
    ]
    props = (schema or {}).get("properties") or {}
    required = set((schema or {}).get("required") or []) | set(missing)
    if props:
        accepted = [
            f"{n} ({(props[n] or {}).get('type', 'any')}{', required' if n in required else ''})" for n in props
        ]
    else:
        accepted = [f"{n}{' (required)' if n in required else ''}" for n in named]
    parts = [f"Tool '{tool_name}' was called with arguments it does not accept."]
    if unknown:
        parts.append("Unknown: " + ", ".join(unknown) + ".")
    if missing:
        parts.append("Missing: " + ", ".join(missing) + ".")
    parts.append("Accepted parameters: " + (", ".join(accepted) or "none") + ".")
    parts.append("Nothing was run; call it again using only these parameters.")
    return " ".join(parts)


@dataclass
class ToolRegistration:
    definition: ToolDefinition
    handler: Callable[..., Any]
    origin: str = "platform"
    risk: str = ""  # read_only / write / network / destructive (CARD-539 D11); empty = policy defaults


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
        *,
        origin: str = "platform",
        risk: str = "",
    ) -> None:
        """Register a tool handler function.

        ``origin`` is catalog metadata (platform, native_custom or mcp).
        """
        definition = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
        )
        self._tools[name] = ToolRegistration(
            definition=definition, handler=handler, origin=origin or "platform", risk=str(risk or "")
        )

    def get_tool_risk(self, name: str) -> str:
        """Declared risk tier of a registered tool; empty when undeclared or absent."""
        reg = self._tools.get(name)
        return reg.risk if reg else ""

    def get_tool_origin(self, name: str) -> str:
        """Catalog origin for a registered tool. Empty when the name is absent."""
        reg = self._tools.get(name)
        if reg is None:
            return ""
        return str(reg.origin or "platform")

    def mount_mcp_tool(
        self,
        definition: ToolDefinition,
        handler: Callable[..., Any],
        name: Optional[str] = None,
    ) -> None:
        """Mount an external MCP tool definition and dispatch handler [REQ-MCP-002].

        Mount/list is not authorization [CARD-225]: callers must still pass
        ToolPolicyGate + matched capability subset before execute.
        """
        tool_name = name or definition.name
        self._tools[tool_name] = ToolRegistration(definition=definition, handler=handler)

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

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check whether a tool name is registered."""
        return name in self._tools

    def get_tools_for_agent(self, agent: AgentProfile) -> List[ToolDefinition]:
        """Registered tools the agent may call: exactly resolve_allowed_tools (ADR-0061); all are sent (ADR-0064)."""
        from src.application.agent_skills.allowed_tools import resolve_allowed_tools

        allowed = resolve_allowed_tools(agent)
        return [reg.definition for name, reg in self._tools.items() if name in allowed]

    async def execute(
        self,
        tool_call: ToolCall,
        agent: AgentProfile,
        session_id: Optional[str] = None,
        approval_mode: Optional[str] = None,
        job_id: Optional[str] = None,
        state_store: Optional[Any] = None,
        offered: Optional[Collection[str]] = None,
    ) -> ToolResult:
        """
        Execute a tool call after verifying RBAC permissions against the agent profile.

        ``offered``: the tool names sent to the model on the call that produced this tool call. When given,
        a tool outside it is refused even if the agent is allowed it (CARD-578). Platform-side runs (an
        approved HITL resume, routines replaying an approved call) pass None and are checked against the
        allowed set only.
        """
        mode = "run" if str(approval_mode or "").strip().lower() == "run" else "ask"
        store = state_store or self.state_store
        # CARD-519: credentials live only in this task's tool context (a ContextVar), never in the process-global
        # os.environ where concurrent tool calls of other agents (and their subprocesses) could read them.
        resolved_creds: Dict[str, str] = {}
        if store and getattr(agent, "allowed_credentials", None):
            for cid in agent.allowed_credentials:
                try:
                    cred = store.get_credential(cid)
                    if cred and cred.secret:
                        resolved_creds[cid] = cred.secret
                except Exception:
                    pass

        token = _tool_context.set(
            {
                "agent_id": agent.id,
                "session_id": session_id,
                "approval_mode": mode,
                "job_id": job_id,
                "allowed_skill": list(getattr(agent, "allowed_skill", None) or []),
                "template_folder": getattr(agent, "template_folder", None),  # CARD-603
                "credentials": resolved_creds,
            }
        )
        try:
            return await self._execute_inner(tool_call, agent, offered=offered)
        finally:
            _tool_context.reset(token)

    async def run_platform_verifier(self, tool_call: ToolCall, agent: AgentProfile) -> ToolResult:
        """Run a platform checker (PLATFORM_VERIFIER_TOOLS) for reflexion; not a model tool call."""
        from src.application.agent_skills.allowed_tools import PLATFORM_VERIFIER_TOOLS, AllowedTools

        name = tool_call.name if tool_call.name in PLATFORM_VERIFIER_TOOLS else ""
        only = AllowedTools(ordered=(name,), provenance={name: ("platform",)}) if name else AllowedTools()
        return await self._execute_inner(tool_call, agent, allowed=only)

    async def _execute_inner(
        self, tool_call: ToolCall, agent: AgentProfile, allowed: Any = None, offered: Optional[Collection[str]] = None
    ) -> ToolResult:
        start_time = time.perf_counter()

        # 1. Verify RBAC authorization: the one allowed-tools function (ADR-0061)
        from src.application.agent_skills.allowed_tools import resolve_allowed_tools

        if allowed is None:
            allowed = resolve_allowed_tools(agent)

        # Exact names only: no bare-name suffix match to mcp_* tools (CARD-578).
        target_name = tool_call.name
        if target_name not in allowed:
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"Tool '{tool_call.name}' is not authorized for agent '{agent.id}'.",
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )
        # CARD-578: only a tool that was sent on this model call may run.
        if offered is not None and target_name not in offered:
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"tool_not_offered:Tool '{tool_call.name}' was not in the tools sent on this call, so it is not authorized here.",
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 2. Verify tool existence
        registration = self._tools.get(target_name)
        if not registration:
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                output=None,
                success=False,
                error=f"Tool '{tool_call.name}' not found in system registry.",
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

        # 3. Execute tool handler
        try:
            handler = registration.handler
            args = unwrap_raw_arguments(handler, tool_call.arguments or {})
            mismatch = argument_mismatch_error(
                tool_call.name, handler, getattr(registration.definition, "parameters", None), args
            )
            if mismatch:
                return ToolResult(
                    call_id=tool_call.id,
                    tool_name=tool_call.name,
                    output=None,
                    success=False,
                    error=mismatch,
                    duration_ms=(time.perf_counter() - start_time) * 1000,
                )

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
