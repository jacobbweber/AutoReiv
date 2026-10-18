"""
Agent Kernel ReAct Loop & Event Streamer [REQ-KERNEL-003, REQ-KERNEL-006, CARD-712].
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Collection, Dict, List, Optional, Tuple

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.context_compactor import (
    ContextCompactor,
    resolve_agent_context_limit,
    resolve_max_tool_chars,
)
from src.application.kernel.empty_reply import is_empty_reply
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.json_safe import to_jsonable
from src.application.kernel.model_resolver import (
    ensure_agent_provider_adapter,
    is_model_compatible_with_provider,
    resolve_agent_model,
)
from src.application.kernel.react_loop import execute_react_loop
from src.application.kernel.reply_limits import reply_token_limit, resolve_reply_limits
from src.application.kernel.reply_rules import (
    drop_false_not_done,
    near_miss_mentions,
    needs_parts_check,
    parse_parts_check,
    parts_check_prompt,
)
from src.application.kernel.system_prompt_builder import (
    build_effective_system_message,
    turn_tools_and_system_message,
)
from src.application.kernel.tool_registry import ScopedToolRegistry, tool_not_offered_error
from src.application.orchestration.capability_detector import CapabilityDetector
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
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

# CARD-562: the Active Selected Project prompt names only tools this agent may call.
_PROJECT_GUIDANCE_TOOLS: tuple[str, ...] = (
    "read_project_file",
    "search_project",
    "list_project_dir",
    "write_project_file",
    "patch_project_file",
)


def project_tool_guidance(allowed_tools: "set[str] | frozenset[str]") -> str:
    """Project tool guidance built only from the agent's resolved allowed tools [CARD-562]."""
    names = [t for t in _PROJECT_GUIDANCE_TOOLS if t in allowed_tools]
    parts: list[str] = []
    if names:
        parts.append(f"Use {', '.join(names)} to work with files inside this project.")
    if "run_project_checks" in allowed_tools:
        parts.append("Run the project's checks (AGENTS.md ## Checks) with run_project_checks.")
    elif "cli_exec" in allowed_tools:
        parts.append("Use cli_exec to run tests and scripts within this directory.")
    return " ".join(parts)


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
        tool_policy_gate: Optional[Any] = None,
    ):
        self.gateway = gateway
        self.tool_registry = tool_registry
        self.state_store = state_store
        self.telemetry = telemetry
        self.hitl_engine = hitl_engine
        if tool_policy_gate is not None:
            self.tool_policy_gate = tool_policy_gate
        else:
            from src.application.safety.tool_policy_gate import ToolPolicyGate

            self.tool_policy_gate = ToolPolicyGate(store=state_store)
        self.react_state: Optional[ReactState] = None
        self.data_dir = data_dir
        self.user_skill_catalog = user_skill_catalog
        self.ace_skill_id: Optional[str] = None
        self._ace_tool_errors: List[Dict[str, Any]] = []
        self._turn_matched_capability_ids: Optional[list] = None
        self._turn_planning_phase: bool = False
        self._last_turn_tool_stats: Dict[str, Any] = {}
        self._last_progressive_skills: List[str] = []
        self._last_episodic_memory: List[str] = []
        self._turn_depth: int = 0
        self.capability_gap_repo = CapabilityGapRepository(state_store)

    def _snapshot_turn_state(self) -> Dict[str, Any]:
        return {
            "react_state": self.react_state,
            "_ace_tool_errors": list(self._ace_tool_errors or []),
            "_turn_matched_capability_ids": (
                list(self._turn_matched_capability_ids)
                if isinstance(self._turn_matched_capability_ids, list)
                else self._turn_matched_capability_ids
            ),
            "_turn_planning_phase": self._turn_planning_phase,
            "_last_turn_tool_stats": dict(self._last_turn_tool_stats or {}),
            "_last_progressive_skills": list(self._last_progressive_skills or []),
            "_last_episodic_memory": list(self._last_episodic_memory or []),
        }

    def _restore_turn_state(self, snap: Dict[str, Any]) -> None:
        for k, v in snap.items():
            setattr(self, k, v)

    def _resolve_ace_data_dir(self) -> Optional[str]:
        if self.data_dir:
            return str(self.data_dir)
        try:
            from src.infrastructure.data.resolver import DataDirResolver

            return str(DataDirResolver().resolve().root)
        except Exception:
            return None

    def _get_scrubber(self) -> Any:
        from src.domain.security.scrubber import TranscriptScrubber

        scrubber = TranscriptScrubber()
        if self.state_store and hasattr(self.state_store, "list_credentials"):
            try:
                creds = self.state_store.list_credentials(include_secret=True)
                scrubber.add_secrets([c.get("secret") for c in creds if c.get("secret")])
            except Exception:
                pass
        return scrubber

    async def execute_and_scrub_tool(
        self,
        tool_call: ToolCall,
        agent: AgentProfile,
        session_id: Optional[str] = None,
        approval_mode: Optional[str] = None,
        job_id: Optional[str] = None,
        offered: Optional[Collection[str]] = None,
    ) -> ToolResult:
        tool_res = await self.tool_registry.execute(
            tool_call,
            agent,
            session_id=session_id,
            approval_mode=approval_mode,
            job_id=job_id,
            state_store=self.state_store,
            offered=offered,
        )
        scrubber = self._get_scrubber()
        if tool_res.output is not None:
            tool_res.output = scrubber.scrub_object(tool_res.output)
            tool_res.output = to_jsonable(tool_res.output)
        if tool_res.error is not None:
            tool_res.error = scrubber.scrub(str(tool_res.error))
        return tool_res

    def _resolve_ace_skill_id(self) -> Optional[str]:
        explicit = (self.ace_skill_id or "").strip()
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
        from src.application.orchestration.ace_online import is_ace_lesson_error

        if not is_ace_lesson_error(error):
            return
        self._ace_tool_errors.append({"tool_name": tool_name, "error": error or "Tool execution error"})

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

            skill_id = self._resolve_ace_skill_id()
            data_dir = self._resolve_ace_data_dir()
            if not skill_id or not data_dir:
                return
            record_failed_turn_delta(
                self.state_store,
                skill_id=skill_id,
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

    def _matched_capability_ids_for_job(
        self, job_id: Optional[str], phase_id: Optional[str] = None, agent: Any = None
    ) -> Optional[list]:
        """Resolve locked matched IDs from durable checkpoint when job/phase-bound [CARD-221/224, CARD-553]."""
        jid = (job_id or "").strip()
        pid = (phase_id or "").strip()
        if not jid and not pid:
            return None
        if pid and self.state_store and not jid:
            getter_phase = getattr(self.state_store, "get_phase", None)
            if callable(getter_phase):
                try:
                    ph = getter_phase(pid)
                    if ph and getattr(ph, "job_id", None):
                        jid = ph.job_id
                except Exception:
                    pass
        if not jid:
            return None
        agent_id = str(getattr(agent, "id", "") or "").strip() if agent is not None else ""
        if agent_id:
            job_getter = getattr(self.state_store, "get_job", None)
            try:
                job = job_getter(jid) if callable(job_getter) else None
            except Exception:
                job = None
            owner = str(getattr(job, "agent_id", "") or "").strip() if job is not None else ""
            if owner and owner != agent_id:
                return None
        getter = getattr(self.state_store, "get_latest_job_phase_checkpoint", None)
        if not callable(getter):
            return None
        try:
            cp = getter(jid)
        except Exception:
            return None
        if cp is None:
            return None
        ids = getattr(cp, "matched_capability_ids", None) or []
        return [str(x) for x in ids]

    def _is_planning_phase(self, phase_id: Optional[str]) -> bool:
        """True when ``phase_id`` is a Formulate (planning) phase [CARD-554]."""
        pid = str(phase_id or "").strip()
        getter = getattr(self.state_store, "get_phase", None)
        if not pid or not callable(getter):
            return False
        try:
            from src.application.orchestration.phase_roles import is_planning_phase

            return is_planning_phase(getter(pid))
        except Exception:
            return False

    def _gate_tool_call(
        self,
        tc: ToolCall,
        session_id: str,
        agent: AgentProfile,
        approval_mode: str = "ask",
        routine_id: Optional[str] = None,
        matched_capability_ids: Optional[list] = None,
        job_id: Optional[str] = None,
        planning_phase: bool = False,
        offered: Optional[Collection[str]] = None,
    ) -> Optional[ToolResult]:
        """Tool policy gate [CARD-221, CARD-578]: ALLOW / REQUIRE_CONFIRM / BLOCK before executor."""
        gate = self.tool_policy_gate
        if gate is None:
            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                output=None,
                success=False,
                error="tool_policy_blocked:ToolPolicyGate missing",
            )
        if offered is not None and tc.name not in offered:
            try:
                exists = any(d.name == tc.name for d in self.tool_registry.list_tools())
            except Exception:
                exists = True
            from src.application.agent_skills.allowed_tools import ticked_skills

            return ToolResult(
                call_id=tc.id,
                tool_name=tc.name,
                output=None,
                success=False,
                error=tool_not_offered_error(tc.name, offered, exists=exists, skills=ticked_skills(agent)),
            )
        registry_names = set()
        try:
            registry_names = {d.name for d in self.tool_registry.list_tools()}
        except Exception:
            registry_names = set()
        risk_of = getattr(self.tool_registry, "get_tool_risk", None)
        decision = gate.evaluate(
            tc,
            agent,
            matched_capability_ids=matched_capability_ids,
            registry_tool_names=registry_names or None,
            tool_risk=risk_of(tc.name) if callable(risk_of) else None,
            planning_phase=planning_phase,
        )
        return gate.apply_to_tool_result(
            decision,
            tc,
            session_id=session_id,
            agent=agent,
            hitl_engine=self.hitl_engine,
            approval_mode=approval_mode,
            routine_id=routine_id,
            job_id=job_id,
        )

    @staticmethod
    def _is_model_compatible_with_provider(model: str, provider_id: str) -> bool:
        return is_model_compatible_with_provider(model, provider_id)

    def _resolve_model(self, agent: AgentProfile) -> str:
        return resolve_agent_model(agent, self.state_store, self.gateway)

    def _ensure_agent_provider_adapter(self, agent: AgentProfile) -> None:
        ensure_agent_provider_adapter(agent, self.gateway)

    def _resolve_context_limit(self, agent: Optional[AgentProfile] = None, model_name: Optional[str] = None) -> int:
        """Unified 3-tier Context Limit Resolution Cascade [CARD-162]."""
        return resolve_agent_context_limit(
            agent=agent,
            state_store=self.state_store,
            fallback_model=model_name,
        )

    def _build_effective_system_message(
        self,
        agent: AgentProfile,
        user_content: Optional[str] = None,
        sent_tools: Optional[Collection[str]] = None,
    ) -> ChatMessage:
        return build_effective_system_message(
            self,
            agent=agent,
            user_content=user_content,
            sent_tools=sent_tools,
            guidance_fn=project_tool_guidance,
        )

    def _own_tool_names(self, agent: AgentProfile) -> set:
        """CARD-615: every tool the agent has (not only this call's)."""
        try:
            return {t.name for t in self.tool_registry.get_tools_for_agent(agent)}
        except Exception:
            return set()

    def _detect_and_record_capability_gap(
        self,
        *,
        agent: AgentProfile,
        user_req_text: str,
        assistant_response: Optional[str],
        history: List[Any],
        session_id: str,
        streamed: bool = False,
    ) -> Any:
        """Detect missing capability for plain or streamed turn and record gap [CARD-663, CARD-681]."""
        own = self._own_tool_names(agent) | near_miss_mentions(history)
        if streamed:
            gap = CapabilityDetector.detect(
                user_prompt=user_req_text,
                assistant_response=assistant_response,
                own_tools=own,
            )
        else:
            gap = CapabilityDetector.detect(
                user_prompt=user_req_text,
                assistant_response=assistant_response,
                own_tools=own,
            )
        if gap:
            try:
                self.capability_gap_repo.create_gap(
                    agent_id=agent.id,
                    user_prompt=gap.user_prompt,
                    missing_capability=gap.missing_capability,
                    context_summary=gap.context_summary,
                    suggested_tool_name=gap.suggested_tool_name,
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning("Failed to record capability gap: %s", e)
        return gap

    def offered_tool_names(
        self, agent: AgentProfile, job_id: Optional[str] = None, phase_id: Optional[str] = None
    ) -> List[str]:
        """The tools a turn of ``agent`` in this job phase is sent, by name [CARD-665]."""
        ids = self._matched_capability_ids_for_job(job_id=job_id, phase_id=phase_id, agent=agent)
        tools = self._resolve_active_tools(
            agent,
            matched_capability_ids=ids if ids is not None else [],
            planning_phase=self._is_planning_phase(phase_id),
        )
        return [t.name for t in tools]

    def _turn_tools_and_system_message(
        self,
        agent: AgentProfile,
        user_content: Optional[str],
        history: List[Any],
        session_id: Optional[str] = None,
    ) -> Tuple[List[Any], set[str], ChatMessage]:
        return turn_tools_and_system_message(self, agent, user_content, history, session_id=session_id)

    def _resolve_active_tools(
        self,
        agent: AgentProfile,
        user_content: Optional[str] = None,
        matched_capability_ids: Optional[list] = None,
        planning_phase: Optional[bool] = None,
        session_id: Optional[str] = None,
        history: Optional[List[Any]] = None,
    ) -> List[Any]:
        """Resolve active tools for the current step [CARD-578, CARD-688]."""
        from src.application.skills.session_skills import resolve_turn_active_tools

        ids = matched_capability_ids
        if ids is None:
            ids = getattr(self, "_turn_matched_capability_ids", None)
        if planning_phase is None:
            planning_phase = bool(getattr(self, "_turn_planning_phase", False))
        return resolve_turn_active_tools(
            self.tool_registry,
            agent,
            matched_capability_ids=ids,
            planning_phase=planning_phase,
            session_id=session_id,
            history=history,
        )

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
        Execute a full synchronous/batched ReAct agent turn via the unified ReAct loop [CARD-712].
        """
        nested_snap = self._snapshot_turn_state() if self._turn_depth > 0 else None
        self._turn_depth += 1
        max_tool_chars_fn = resolve_max_tool_chars  # supplies max_tool_chars to ContextCompactor.compact
        result_box: Dict[str, Any] = {}
        try:
            async for _ in execute_react_loop(
                self,
                agent=agent,
                session_id=session_id,
                user_content=user_content,
                save_to_history=save_to_history,
                approval_mode=approval_mode,
                resume=resume,
                routine_id=routine_id,
                phase_id=phase_id,
                job_id=job_id,
                stream=False,
                max_tool_chars_fn=max_tool_chars_fn,
                result_box=result_box,
            ):
                pass
            return result_box["message"]
        finally:
            self._turn_depth -= 1
            if nested_snap is not None:
                self._restore_turn_state(nested_snap)

    async def stream_turn(
        self,
        agent: AgentProfile,
        session_id: str,
        user_content: Optional[str] = None,
        approval_mode: str = "ask",
        resume: bool = False,
        routine_id: Optional[str] = None,
        phase_id: Optional[str] = None,
        job_id: Optional[str] = None,
        parts_request: Optional[str] = None,
        save_to_history: bool = True,
    ) -> AsyncIterator[KernelEvent]:
        """
        Execute an asynchronous streaming agent turn via the unified ReAct loop [CARD-712].
        """
        nested_snap = self._snapshot_turn_state() if self._turn_depth > 0 else None
        self._turn_depth += 1
        max_tool_chars_fn = resolve_max_tool_chars  # supplies max_tool_chars to ContextCompactor.compact
        try:
            async for ev in execute_react_loop(
                self,
                agent=agent,
                session_id=session_id,
                user_content=user_content,
                save_to_history=save_to_history,
                approval_mode=approval_mode,
                resume=resume,
                routine_id=routine_id,
                phase_id=phase_id,
                job_id=job_id,
                parts_request=parts_request,
                stream=True,
                max_tool_chars_fn=max_tool_chars_fn,
            ):
                yield ev
        finally:
            self._turn_depth -= 1
            if nested_snap is not None:
                self._restore_turn_state(nested_snap)

    async def _skipped_parts_note(
        self, model_name: str, user_text: str, tools_ran: List[str], reply: str, context_limit: int
    ) -> str:
        """CARD-599 (b): a short no-tools check on the same model; "Not done: ..." lines for skipped parts, else ""."""
        if not needs_parts_check(user_text, reply):
            return ""
        try:
            req = CompletionRequest(
                model=model_name,
                messages=[ChatMessage(role=Role.USER, content=parts_check_prompt(user_text, tools_ran, reply))],
                tools=None,
                num_ctx=context_limit,
                max_tokens=reply_token_limit(resolve_reply_limits(self.state_store)[0], context_limit),
            )
            resp = await self.gateway.complete(req)
            msg = getattr(resp, "message", None)
            return drop_false_not_done(parse_parts_check(getattr(msg, "content", None) or ""), tools_ran)
        except Exception as exc:
            logger.warning("skipped-parts check failed: %s", exc)
            return ""

    async def _final_answer_without_tools(
        self,
        model_name: str,
        system_msg: ChatMessage,
        history: List[ChatMessage],
        context_limit: int,
        instruction: str,
    ) -> str:
        """CARD-551/461: one last model call with no tools; "" when it fails, is empty or only tries to call tools."""
        try:
            messages = ContextCompactor.compact(
                [system_msg] + list(history),
                model_name=model_name,
                max_tokens=max(1000, int(context_limit * 0.75)),
                keep_last_n_turns=4,
                max_tool_chars=resolve_max_tool_chars(context_limit),
                preserve_root_intent=True,
            )
            messages = list(messages) + [ChatMessage(role=Role.USER, content=instruction)]
            req = CompletionRequest(
                model=model_name,
                messages=messages,
                tools=None,
                num_ctx=context_limit,
                max_tokens=reply_token_limit(resolve_reply_limits(self.state_store)[0], context_limit),
            )
            resp = await self.gateway.complete(req)
            msg = getattr(resp, "message", None)
            text = (getattr(msg, "content", None) or getattr(resp, "text", None) or "").strip()
            return "" if is_empty_reply(text, None) else text
        except Exception as exc:
            logger.warning("final no-tools answer failed: %s", exc)
            return ""

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
