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
from src.application.orchestration.handoff_engine import looks_like_provider_failure
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
from src.domain.orchestration.models import ReactState
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

# Nested run_turn (handoffs, routines) must not inherit Chat's 131k window.
# Live CARD-001 complete() at num_ctx=131072 sent zero bytes for 90s+ and
# tripped the Ollama read timeout. 32k returns a tool call in seconds.
NESTED_COMPLETE_MAX_CTX = 32768
NESTED_COMPLETE_MAX_TOKENS = 8192


def parse_nested_park_payload(content: str):
    """Return a nested HITL park dict, or None."""
    try:
        parsed = json.loads(content or "")
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict) and parsed.get("status") == "approval_required" and parsed.get("approval_id"):
        return parsed
    return None


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
        data_dir: Optional[str] = None,
        user_skill_catalog: Optional[Any] = None,
    ):
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.state_store = state_store
        self.telemetry = telemetry
        self.hitl_engine = hitl_engine
        self.react_state: Optional[ReactState] = None
        self.data_dir = data_dir
        self.user_skill_catalog = user_skill_catalog
        self.ace_pack_id: Optional[str] = None
        self._ace_tool_errors: List[Dict[str, Any]] = []



    def _resolve_ace_data_dir(self) -> Optional[str]:
        if self.data_dir:
            return str(self.data_dir)
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            return str(DataDirResolver().resolve().root)
        except Exception:
            return None

    def _resolve_ace_pack_id(self) -> Optional[str]:
        explicit = (self.ace_pack_id or "").strip()
        if explicit:
            return explicit
        names = [str(item.get("tool_name") or "") for item in self._ace_tool_errors]
        catalog = self.user_skill_catalog
        if catalog is None:
            data_dir = self._resolve_ace_data_dir()
            if data_dir:
                from pathlib import Path as _Path

                from src.application.skills.user_catalog import UserSkillCatalog

                catalog = UserSkillCatalog(skills_dir=_Path(data_dir) / "skills")
        if catalog is None:
            return None
        try:
            manifests = catalog.list_manifests()
        except Exception:
            return None
        for manifest in manifests:
            slug = str(manifest.id).replace("-", "_").lower()
            if slug and any(slug in n.lower().replace("-", "_") for n in names if n):
                return manifest.id
        return None

    def _ace_note_tool(self, tool_name: str, success: bool, error: Optional[str]) -> None:
        if success:
            return
        self._ace_tool_errors.append(
            {"tool_name": tool_name, "error": error or "Tool execution error"}
        )

    def _ace_flush_failed_turn(
        self,
        *,
        session_id: str,
        agent_id: str,
        failed: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Post-turn Reflector hook. Never raises into the turn [REQ-IMPROVE-001]."""
        errors = list(self._ace_tool_errors or [])
        if not failed and not errors:
            return
        try:
            from src.application.orchestration.ace_online import record_failed_turn_delta

            pack_id = self._resolve_ace_pack_id()
            data_dir = self._resolve_ace_data_dir()
            if not pack_id or not data_dir:
                return
            record_failed_turn_delta(
                self.state_store,
                pack_id=pack_id,
                data_dir=data_dir,
                session_id=session_id,
                agent_id=agent_id,
                error_message=error_message,
                tool_errors=errors,
                catalog=self.user_skill_catalog,
            )
        except Exception as exc:
            logger.debug("online ACE skipped: %s", exc)
        finally:
            self._ace_tool_errors = []

    def _transition_react_state(
        self,
        state: ReactState,
        turn_idx: int,
        *,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
    ) -> Optional[KernelEvent]:
        """Overlay ReAct state and persist when phase_id is in scope [REQ-KERNEL-001]."""
        if self.react_state == state:
            return None
        self.react_state = state
        job_status = None
        phase_name = None
        resolved_job_id = job_id
        resolved_agent = assigned_agent_id
        if phase_id:
            try:
                get_phase = getattr(self.state_store, "get_phase", None)
                update_phase = getattr(self.state_store, "update_phase", None)
                if get_phase and update_phase:
                    phase = get_phase(phase_id)
                    phase.react_state = state
                    update_phase(phase)
                    phase_name = phase.name
                    resolved_job_id = resolved_job_id or phase.job_id
                    resolved_agent = resolved_agent or phase.assigned_agent_id
                    get_job = getattr(self.state_store, "get_job", None)
                    if get_job:
                        try:
                            job = get_job(phase.job_id)
                            status = job.status
                            job_status = status.value if hasattr(status, "value") else str(status)
                        except Exception:
                            pass
            except Exception as exc:
                logger.debug("react_state persist skipped for phase %s: %s", phase_id, exc)
        return KernelEvent(
            event_type=KernelEventType.REACT_STATE,
            react={
                "react_state": state.value,
                "turn_idx": turn_idx,
                "job_id": resolved_job_id,
                "phase_id": phase_id,
                "assigned_agent_id": resolved_agent,
                "job_status": job_status,
                "phase_name": phase_name,
            },
        )

    def _gate_tool_call(self, tc: ToolCall, session_id: str, agent: AgentProfile, approval_mode: str = "ask", routine_id: Optional[str] = None) -> Optional[ToolResult]:
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
                routine_id=routine_id,
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
        from src.application.skills.user_catalog import render_skill_index

        skill_block = render_skill_index(
            getattr(agent, "allowed_skill", None),
            self.user_skill_catalog,
        )
        if skill_block:
            base_prompt = f"{base_prompt}\n\n{skill_block}"
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
        resume: bool = False,
        routine_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> ChatMessage:
        """
        Execute a full synchronous/batched ReAct agent turn with tool execution.

        When resume=True, continue from persisted history without appending a USER message.
        """
        self._ace_tool_errors = []
        if resume:
            user_content = None
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
        react_ctx = {
            "phase_id": phase_id,
            "job_id": job_id,
            "assigned_agent_id": agent.id,
        }

        for turn_idx in range(agent.max_turns):
            self._transition_react_state(ReactState.THINKING, turn_idx, **react_ctx)
            turn_start = time.perf_counter()
            context_limit = self._resolve_context_limit(model_name)
            nested_ctx = min(context_limit, NESTED_COMPLETE_MAX_CTX)
            compacted_messages = ContextCompactor.compact(
                [system_msg] + history,
                model_name=model_name,
                max_tokens=max(1000, int(nested_ctx * 0.75)),
                keep_last_n_turns=4,
                preserve_root_intent=True,
            )
            req = CompletionRequest(
                model=model_name,
                messages=compacted_messages,
                tools=active_tools or None,
                num_ctx=nested_ctx,
                max_tokens=NESTED_COMPLETE_MAX_TOKENS,
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
                self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=str(e)
                )
                raise

            assistant_msg = resp.message

            # Text generation repetition loop check [REQ-RESIL-003]
            if assistant_msg.content and cycle_detector.record_and_check_text(assistant_msg.content):
                self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive text generation loop.",
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id,
                    agent_id=agent.id,
                    failed=True,
                    error_message=cycle_msg.content,
                )
                return cycle_msg

            # If no tool calls, turn is complete
            if not assistant_msg.tool_calls:
                self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                return assistant_msg

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(assistant_msg.tool_calls):
                self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                if save_to_history:
                    self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id,
                    agent_id=agent.id,
                    failed=True,
                    error_message=cycle_msg.content,
                )
                return cycle_msg

            self._transition_react_state(ReactState.CALLING_TOOLS, turn_idx, **react_ctx)

            # Handle tool calls
            if save_to_history:
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
            history.append(assistant_msg)

            for tc in assistant_msg.tool_calls:
                gated = self._gate_tool_call(tc, session_id, agent, approval_mode=approval_mode, routine_id=routine_id)
                if gated is not None:
                    tool_res = gated
                else:
                    tool_res = await self.tool_registry.execute(tc, agent, session_id=session_id, approval_mode=approval_mode, job_id=react_ctx.get("job_id"))
                self.telemetry.record_tool_span(
                    agent_id=agent.id,
                    session_id=session_id,
                    tool_name=tc.name,
                    duration_ms=tool_res.duration_ms,
                    success=tool_res.success,
                    error_message=tool_res.error,
                )
                self._ace_note_tool(tc.name, tool_res.success, tool_res.error)

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
                    self._transition_react_state(ReactState.PARKED, turn_idx, **react_ctx)
                    return parked_msg

        self._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self._ace_flush_failed_turn(
            session_id=session_id, agent_id=agent.id, failed=True, error_message=limit_msg.content
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
        resume: bool = False,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> AsyncIterator[KernelEvent]:
        """
        Execute an asynchronous streaming agent turn with live token and tool lifecycle events.

        When resume=True or user_content is empty, continue from persisted history
        without appending a USER message [REQ-HITL-034].
        """
        self._ace_tool_errors = []
        if resume:
            user_content = None
        if user_content:
            user_msg = ChatMessage(role=Role.USER, content=user_content)
            self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=user_msg)

        react_ctx = {
            "phase_id": phase_id,
            "job_id": job_id,
            "assigned_agent_id": agent.id,
        }
        history = self.state_store.get_messages(session_id=session_id)
        if resume:
            replay = self._nested_park_replay_events(history)
            if replay:
                parked_ev = self._transition_react_state(ReactState.PARKED, 0, **react_ctx)
                if parked_ev:
                    yield parked_ev
                for ev in replay:
                    yield ev
                return
        system_msg = self._build_effective_system_message(agent, user_content)
        active_tools = self._resolve_active_tools(agent, user_content)
        model_name = self._resolve_model(agent)

        cycle_detector = CycleDetector(max_repeats=3)

        for turn_idx in range(agent.max_turns):
            thinking_ev = self._transition_react_state(ReactState.THINKING, turn_idx, **react_ctx)
            if thinking_ev:
                yield thinking_ev
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

            # Close the parent LLM HTTP stream BEFORE tools (child handoff complete()).
            stream_gen = None
            try:
                stream_gen = self.gateway.stream(req, demux_reasoning=True)
                async for chunk in stream_gen:
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
                    if chunk.is_finished:
                        break
            except Exception as e:
                failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=str(e)
                )
                yield KernelEvent(event_type=KernelEventType.ERROR, content=str(e), is_finished=True)
                return
            finally:
                closer = getattr(stream_gen, "aclose", None)
                if callable(closer):
                    await closer()

            full_content = "".join(accumulated_content)

            # Text generation repetition loop check [REQ-RESIL-003]
            if full_content and cycle_detector.record_and_check_text(full_content):
                failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive text generation loop.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=cycle_msg.content
                )
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=cycle_msg.content, is_finished=True)
                return

            # If no tool calls returned, stream is complete
            if not collected_tool_calls:
                done_ev = self._transition_react_state(ReactState.DONE, turn_idx, **react_ctx)
                if done_ev:
                    yield done_ev
                assistant_msg = ChatMessage(role=Role.ASSISTANT, content=full_content)
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=assistant_msg)
                self._ace_flush_failed_turn(session_id=session_id, agent_id=agent.id, failed=False)
                yield KernelEvent(event_type=KernelEventType.TURN_END, content=full_content, is_finished=True)
                return

            # Tool call cycle detection [REQ-RESIL-003]
            if cycle_detector.record_and_check(collected_tool_calls):
                failed_ev = self._transition_react_state(ReactState.FAILED, turn_idx, **react_ctx)
                if failed_ev:
                    yield failed_ev
                cycle_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content="Execution terminated: Detected repetitive cycle calling tools.",
                )
                self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=cycle_msg)
                self._ace_flush_failed_turn(
                    session_id=session_id, agent_id=agent.id, failed=True, error_message=cycle_msg.content
                )
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

            calling_ev = self._transition_react_state(ReactState.CALLING_TOOLS, turn_idx, **react_ctx)
            if calling_ev:
                yield calling_ev

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
                    tool_res = await self.tool_registry.execute(tc, agent, session_id=session_id, approval_mode=approval_mode, job_id=react_ctx.get("job_id"))
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
                self._ace_note_tool(tc.name, tool_res.success, tool_res.error)

                yield KernelEvent(
                    event_type=KernelEventType.TOOL_END,
                    tool_result=tool_res,
                )

                parked = False
                if tool_res.error and str(tool_res.error).startswith("approval_required:"):
                    parked = True
                nested_out = tool_res.output if isinstance(tool_res.output, dict) else None
                if nested_out and nested_out.get("status") == "approval_required" and nested_out.get("approval_id"):
                    parked = True

                if is_handoff_tool:
                    args = tc.arguments if isinstance(tc.arguments, dict) else {}
                    target_id = args.get("target_agent") or args.get("target_agent_id") or "specialist"
                    output_blob = (
                        json.dumps(tool_res.output)
                        if isinstance(tool_res.output, (dict, list))
                        else str(tool_res.output or "")
                    )
                    if parked:
                        handoff_status = "approval_required"
                    elif (
                        (not tool_res.success)
                        or looks_like_provider_failure(output_blob)
                        or looks_like_provider_failure(str(tool_res.error or ""))
                    ):
                        handoff_status = "failed"
                    else:
                        handoff_status = "completed"
                    yield KernelEvent(
                        event_type=KernelEventType.HANDOFF_COMPLETE,
                        handoff={
                            "recipient": target_id,
                            "status": handoff_status,
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

                if parked:
                    parked_ev = self._transition_react_state(ReactState.PARKED, turn_idx, **react_ctx)
                    if parked_ev:
                        yield parked_ev
                    park_text = ""
                    if isinstance(tool_res.output, dict):
                        park_text = str(tool_res.output.get("message") or "")
                    yield KernelEvent(
                        event_type=KernelEventType.TURN_END,
                        content=park_text,
                        is_finished=True,
                    )
                    return

        # If turn limit reached
        failed_ev = self._transition_react_state(ReactState.FAILED, agent.max_turns, **react_ctx)
        if failed_ev:
            yield failed_ev
        limit_msg = ChatMessage(
            role=Role.ASSISTANT,
            content=f"Execution terminated: Max turn budget of {agent.max_turns} reached.",
        )
        self._ace_flush_failed_turn(
            session_id=session_id, agent_id=agent.id, failed=True, error_message=limit_msg.content
        )
        self.state_store.save_message(session_id=session_id, agent_id=agent.id, message=limit_msg)
        yield KernelEvent(
            event_type=KernelEventType.TURN_END,
            content=limit_msg.content,
            is_finished=True,
        )

    def _nested_park_replay_events(self, history: List[ChatMessage]) -> List[KernelEvent]:
        """Re-emit a nested child park on parent resume [REQ-HITL-038]."""
        last_tool = None
        for msg in reversed(list(history or [])):
            if msg.role == Role.TOOL:
                last_tool = msg
                break
        parked = parse_nested_park_payload(last_tool.content if last_tool else "")
        if not parked:
            return []
        tool_name = parked.get("tool_name") or (last_tool.name if last_tool else "tool") or "tool"
        arguments = parked.get("arguments") if isinstance(parked.get("arguments"), dict) else {}
        message = str(parked.get("message") or "Approval required")
        return [
            KernelEvent(
                event_type=KernelEventType.APPROVAL_REQUIRED,
                content=message,
                approval_id=str(parked.get("approval_id")),
                tool_call={
                    "id": (last_tool.tool_call_id if last_tool else "") or "",
                    "name": tool_name,
                    "arguments": arguments,
                },
            ),
            KernelEvent(
                event_type=KernelEventType.HANDOFF_COMPLETE,
                handoff={
                    "recipient": parked.get("recipient_agent_id") or "specialist",
                    "status": "approval_required",
                },
            ),
            KernelEvent(
                event_type=KernelEventType.TURN_END,
                content=message,
                is_finished=True,
            ),
        ]

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
