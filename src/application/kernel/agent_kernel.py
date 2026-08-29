"""
Agent Kernel ReAct Loop & Event Streamer [REQ-KERNEL-003, REQ-KERNEL-006].
"""

import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.context_compactor import ContextCompactor, get_model_context_limit
from src.application.kernel.cycle_detector import CycleDetector
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.command_filter import DangerousCommandFilter
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    Role,
    ToolCall,
)
from src.domain.kernel.models import (
    AgentProfile,
    KernelEvent,
    KernelEventType,
    ToolResult,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)


class AgentKernel:
    """
    Orchestrates the ReAct execution loop, scoped tool dispatching,
    conversation state persistence, and telemetry collection.
    """

    def __init__(
        self,
        gateway: MultiProviderGateway,
        tool_registry: ScopedToolRegistry,
        state_store: SQLiteStateStore,
        telemetry: TelemetryCollector,
        hitl_engine: Optional[HITLApprovalEngine] = None,
    ):
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.state_store = state_store
        self.telemetry = telemetry
        self.hitl_engine = hitl_engine


    def _gate_tool_call(self, tc: ToolCall, session_id: str, agent: AgentProfile, approval_mode: str = "ask") -> Optional[ToolResult]:
        """
        Return a ToolResult to short-circuit (deny/park), or None to execute.
        When parked, the ToolResult.output includes approval_id and status parked.
        """
        if tc.name not in getattr(agent, "allowed_tool_names", []):
            return None
        args = tc.arguments if isinstance(tc.arguments, dict) else {}
        if tc.name == "cli_exec":
            command = str(args.get("command") or args.get("cmd") or "")
            is_bad, reason = DangerousCommandFilter.is_dangerous(command)
            if is_bad:
                return ToolResult(
                    call_id=tc.id,
                    tool_name=tc.name,
                    output=None,
                    success=False,
                    error=reason or "Prohibited dangerous command",
                )
        mode = "run" if str(approval_mode or "").strip().lower() == "run" else "ask"
        if mode != "run" and self.hitl_engine and self.hitl_engine.requires_approval(tc):
            approval_id = self.hitl_engine.park_tool_call(
                session_id=session_id,
                agent_id=agent.id,
                tool_call=tc,
            )
            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                output={
                    "status": "parked",
                    "approval_id": approval_id,
                    "message": f"Parked for operator approval ({approval_id}). The tool was not executed.",
                },
                success=False,
                error=f"approval_required:{approval_id}",
            )
        return None

    def _resolve_model(self, agent: AgentProfile) -> str:
        """
        Multi-Tier Purpose & Provider to Model Cascade Resolution:
        1. Agent explicit model override (if not 'default' or empty)
        2. Purpose Matrix slot mapping for agent.purpose
        3. Purpose Matrix default_model
        4. Provider settings default_model_id
        5. Gateway default_model_id
        6. Gateway default provider / fallback
        """
        if agent.model and agent.model != "default":
            return agent.model

        if self.state_store:
            matrix_data = self.state_store.get_setting("purpose_matrix")
            if isinstance(matrix_data, dict):
                raw_purposes = matrix_data.get("purposes")
                purposes_map: Dict[Any, Any] = raw_purposes if isinstance(raw_purposes, dict) else matrix_data
                purpose_key = agent.purpose.value if hasattr(agent.purpose, "value") else str(agent.purpose)
                mapped_model = purposes_map.get(purpose_key)
                if mapped_model and mapped_model != "default":
                    return mapped_model
                if matrix_data.get("default_model") and matrix_data.get("default_model") != "default":
                    return matrix_data["default_model"]

            prov_data = self.state_store.get_setting("provider_settings")
            if isinstance(prov_data, dict):
                def_model = prov_data.get("default_model_id")
                if def_model and def_model != "default":
                    return def_model

        if self.gateway and getattr(self.gateway, "default_model_id", None) and self.gateway.default_model_id != "default":
            return self.gateway.default_model_id

        if self.gateway and getattr(self.gateway, "default_provider_id", None):
            return f"{self.gateway.default_provider_id}/default"
        return "default"

    def _resolve_context_limit(self, model_name: str) -> int:
        """Prefer Settings matrix overrides, then the name-based limiter."""
        default_override = None
        model_overrides = None
        if self.state_store:
            matrix_data = self.state_store.get_setting("purpose_matrix")
            if isinstance(matrix_data, dict):
                default_override = matrix_data.get("default_context_window")
                raw_windows = matrix_data.get("model_context_windows")
                if isinstance(raw_windows, dict):
                    model_overrides = raw_windows
        return get_model_context_limit(
            model_name,
            default_override=default_override,
            model_overrides=model_overrides,
        )

    def _build_effective_system_message(
        self,
        agent: AgentProfile,
        user_content: Optional[str] = None,
    ) -> ChatMessage:
        """
        Constructs system prompt enriched with auto-recalled episodic facts [REQ-EPISODIC-003].
        """
        base_prompt = agent.get_effective_system_prompt()
        if user_content and self.state_store and hasattr(self.state_store, "search_facts"):
            try:
                matched_facts = self.state_store.search_facts(query=user_content, limit=4)
                if matched_facts:
                    from src.application.skills.memory_skill import render_memory_context

                    memory_block = render_memory_context(matched_facts)
                    if memory_block:
                        base_prompt = f"{base_prompt}\n\n{memory_block}"
            except Exception as e:
                logger.debug(f"Episodic memory auto-recall skipped: {e}")

        return ChatMessage(role=Role.SYSTEM, content=base_prompt)

    def _resolve_active_tools(self, agent: AgentProfile, user_content: Optional[str] = None) -> List[Any]:
        """
        RBAC allowlist only [REQ-TOOLS-010].
        The full granted set is mounted. Ranking is not applied at turn time.
        """
        _ = user_content  # query ranking is not used at turn time
        return self.tool_registry.get_tools_for_agent(agent)

    async def run_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
        save_to_history: bool = True,
        approval_mode: str = "ask",
    ) -> ChatMessage:
        """
        Execute a full synchronous/batched ReAct agent turn with tool execution.
        """
        if user_content and save_to_history:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        history = list(self.state_store.get_messages(session_id=session_id))
        if user_content and not save_to_history:
            history.append(ChatMessage(role=Role.USER, content=user_content))

        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(agent, user_content)
        model_name = self._resolve_model(agent)

        cycle_detector = CycleDetector(max_repeats=3)

        for turn_idx in range(agent.max_turns):
            turn_start = time.perf_counter()
            context_limit = self._resolve_context_limit(model_name)
            compacted_messages = ContextCompactor.compact(
                [system_msg] + history,
                model_name=model_name,
                max_tokens=max(1000, int(context_limit * 0.75)),
                keep_last_n_turns=4,
                preserve_root_intent=True,
            )
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=active_tools or None,
                num_ctx=context_limit,
            )

            try:
                resp = await self.gateway.complete(req)
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000

                prompt_tokens = resp.usage.get("prompt_tokens", 0) if resp.usage else 0
                comp_tokens = resp.usage.get("completion_tokens", 0) if resp.usage else 0

                self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=resp.model,
                    duration_ms=turn_dur_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=comp_tokens,
                    success=True,
                )
            except Exception as e:
                turn_dur_ms = (time.perf_counter() - turn_start) * 1000
                self.telemetry.record_turn_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    model=model_name,
                    duration_ms=turn_dur_ms,
                    success=False,
                    error_message=str(e),
                )
                raise

            assistant_msg = resp.message

            # Text generation repetition loop check [REQ-RESIL-003]
            if assistant_msg.content and cycle_detector.record_and_check_text(assistant_msg.content):
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive text generation loop.",
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                return cycle_msg

            # If no tool calls, turn is complete
            if not assistant_msg.tool_calls:
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                return assistant_msg

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(assistant_msg.tool_calls):
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                return cycle_msg

            # Handle tool calls
            if save_to_history:
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            for tc in assistant_msg.tool_calls:
                gated = self._gate_tool_call(tc, session_id, agent, approval_mode=approval_mode)
                if gated is not None:
                    tool_res = gated
                else:
                    tool_res = await self.tool_registry.execute(tc, agent, session_id=session_id, approval_mode=approval_mode)
                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_res.success,
                    error_message=tool_res.error,
                )

                if tool_res.success:
                    tool_content = (
                        json.dumps(tool_res.output)
                        if isinstance(tool_res.output, (dict, list))
                        else str(tool_res.output)
                    )
                else:
                    tool_content = tool_res.error or "Tool execution error"

                tool_msg = ChatMessage(
                    role=Role.TOOL,
                    content=tool_content,
                    name=tc.name,
                    tool_call_id=tc.id,
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=tool_msg)
                history.append(tool_msg)

                if tool_res.error and str(tool_res.error).startswith("approval_required:"):
                    parked = {
                        "status": "approval_required",
                        "approval_id": tool_res.output.get("approval_id") if isinstance(tool_res.output, dict) else "",
                        "tool_name": tc.name,
                        "arguments": tc.arguments if isinstance(tc.arguments, dict) else {},
                        "message": tool_res.output.get("message") if isinstance(tool_res.output, dict) else "Approval required",
                    }
                    parked_msg = ChatMessage(role=Role.ASSISTANT, content=json.dumps(parked))
                    if save_to_history:
                        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=parked_msg)
                    return parked_msg

        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        if save_to_history:
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        return limit_msg

    async def stream_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
        approval_mode: str = "ask",
    ) -> AsyncIterator[KernelEvent]:
        """
        Execute an asynchronous streaming agent turn with live token and tool lifecycle events.
        """
        if user_content:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        history = self.state_store.get_messages(session_id=session_id)
        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(agent, user_content)
        model_name = self._resolve_model(agent)

        cycle_detector = CycleDetector(max_repeats=3)

        for turn_idx in range(agent.max_turns):
            context_limit = self._resolve_context_limit(model_name)
            compacted_messages = ContextCompactor.compact(
                [system_msg] + history,
                model_name=model_name,
                max_tokens=max(1000, int(context_limit * 0.75)),
                keep_last_n_turns=4,
                preserve_root_intent=True,
            )
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=active_tools or None,
                num_ctx=context_limit,
                stream=True,
            )

            accumulated_content = []
            accumulated_reasoning = []
            collected_tool_calls: List[ToolCall] = []

            async for chunk in self.gateway.stream(req, demux_reasoning=True):
                if chunk.content or chunk.reasoning_content:
                    if chunk.content:
                        accumulated_content.append(chunk.content)
                    if chunk.reasoning_content:
                        accumulated_reasoning.append(chunk.reasoning_content)
                    yield KernelEvent(
                        event_type=KernelEventType.TOKEN,
                        content=chunk.content,
                        reasoning_content=chunk.reasoning_content,
                    )

                if chunk.tool_calls:
                    collected_tool_calls.extend(chunk.tool_calls)

            full_content = "".join(accumulated_content)

            # Text generation repetition loop check [REQ-RESIL-003]
            if full_content and cycle_detector.record_and_check_text(full_content):
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive text generation loop.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # If no tool calls returned, stream is complete
            if not collected_tool_calls:
                assistant_msg = ChatMessage(role=Role.ASSISTANT, content=full_content)
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=full_content, is_finished=True)
                return

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(collected_tool_calls):
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # Save assistant message with tool calls
            assistant_msg = ChatMessage(
                role=Role.ASSISTANT,
                content=full_content,
                tool_calls=collected_tool_calls,
            )
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            # Execute tool calls
            for tc in collected_tool_calls:
                is_handoff_tool = tc.name == "handoff_to_agent"
                if is_handoff_tool:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    target_id = args.get("target_agent") or args.get("target_agent_id") or "specialist"
                    directive = args.get("task_intent") or args.get("task_directive") or ""
                    yield KernelEvent(
                        event_type=KernelEventType.HANDOFF_START,
                        handoff={
                            "sender": agent.id,
                            "recipient": target_id,
                            "directive": directive,
                        },
                    )

                yield KernelEvent(
                    event_type=KernelEventType.TOOL_START,
                    tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                )

                gated = self._gate_tool_call(tc, session_id, agent, approval_mode=approval_mode)
                if gated is not None:
                    tool_res = gated
                    if tool_res.error and str(tool_res.error).startswith("approval_required:"):
                        approval_id = str(tool_res.output.get("approval_id") if isinstance(tool_res.output, dict) else "")
                        yield KernelEvent(
                            event_type=KernelEventType.APPROVAL_REQUIRED,
                            content=tool_res.output.get("message", "Approval required") if isinstance(tool_res.output, dict) else "Approval required",
                            approval_id=approval_id or None,
                            tool_call={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                            tool_result=tool_res,
                        )
                else:
                    tool_res = await self.tool_registry.execute(tc, agent, session_id=session_id, approval_mode=approval_mode)
                    nested = tool_res.output if isinstance(tool_res.output, dict) else None
                    if nested and nested.get("status") == "approval_required" and nested.get("approval_id"):
                        yield KernelEvent(
                            event_type=KernelEventType.APPROVAL_REQUIRED,
                            content=nested.get("message") or "Approval required",
                            approval_id=str(nested.get("approval_id")),
                            tool_call={
                                "id": tc.id,
                                "name": nested.get("tool_name") or tc.name,
                                "arguments": nested.get("arguments") or {},
                            },
                            tool_result=tool_res,
                        )
                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_res.success,
                    error_message=tool_res.error,
                )

                yield KernelEvent(
                    event_type=KernelEventType.TOOL_END,
                    tool_result=tool_res,
                )

                if is_handoff_tool:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    target_id = args.get("target_agent") or args.get("target_agent_id") or "specialist"
                    yield KernelEvent(
                        event_type=KernelEventType.HANDOFF_COMPLETE,
                        handoff={
                            "recipient": target_id,
                            "status": "completed" if tool_res.success else "failed",
                            "error": tool_res.error,
                        },
                    )

                if tool_res.success:
                    tool_content = (
                        json.dumps(tool_res.output)
                        if isinstance(tool_res.output, (dict, list))
                        else str(tool_res.output)
                    )
                else:
                    tool_content = f"Tool Error: {tool_res.error}"

                tool_msg = ChatMessage(
                    role=Role.TOOL,
                    content=tool_content,
                    tool_call_id=tc.id,
                    name=tc.name,
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=tool_msg)
                history.append(tool_msg)

        # If turn limit reached
        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content=limit_msg.content,
            is_finished=True,
        )

    async def run_verified_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: str,
        verifier_tool_name: Optional[str] = None,
        verifier_args: Optional[Dict[str, Any]] = None,
        max_refinements: int = 3,
    ) -> Dict[str, Any]:
        """Execute a self-verifying turn using ReflexionLoopEngine [REQ-VERIFY-003]."""
        from src.application.kernel.reflexion_engine import ReflexionLoopEngine

        engine = ReflexionLoopEngine(kernel=self, tool_registry=self.tool_registry)
        return await engine.run_reflexion_turn(
            agent=agent,
            session_id=session_id,
            user_content=user_content,
            verifier_tool_name=verifier_tool_name,
            verifier_args=verifier_args,
            max_refinements=max_refinements,
        )
