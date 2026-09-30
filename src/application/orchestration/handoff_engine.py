"""
Isolated Subagent Handoff Execution Engine [REQ-ORCH-003].
Orchestrates isolated child execution loops with recursion depth & turn bounding.
Child path uses stream_turn with a HandoffPacket user message [REQ-ORCH-036, REQ-ORCH-037].
"""

import inspect
import json
import logging
import re
from typing import Any, AsyncIterator, Callable, Optional

from src.domain.agents.profiles import canonical_agent_id
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import DEFAULT_AGENT_MAX_TURNS, AgentProfile, KernelEventType
from src.domain.orchestration.errors import HandoffPacketError
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket, HandoffResult
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

CHILD_SESSION_MARKER = "_child_"
_MIN_CHILD_TURNS = 10
_MAX_CHILD_TURNS = 15
# CARD-563: a card hand-off (hand_off_card) runs a whole card; slice-1 runs needed about 15 tool calls.
_MAX_CARD_HANDOFF_TURNS = 40
# Parent tools whose TOOL row a resumed child writes back to [REQ-HITL-036]; hand_off_card is CARD-563.
PARENT_HANDOFF_TOOLS = ("handoff_to_agent", "hand_off_card")
_PROVIDER_FAILURE_MARKERS = (
    "failed to connect",
    "candidate providers failed",
    "subagent handoff failed",
    "ollama timed out",
    "timed out at",
)


def looks_like_provider_failure(text: str) -> bool:
    """True when child output is a provider/connect failure, not a real completion."""
    blob = (text or "").lower()
    return any(marker in blob for marker in _PROVIDER_FAILURE_MARKERS)


def bound_child_max_turns(envelope_max_turns: int, profile_max_turns: int, cap: int = _MAX_CHILD_TURNS) -> int:
    """Child turn budget: at least 10 (or the profile), never above the cap (15; 40 for a card hand-off)."""
    return min(
        max(int(envelope_max_turns or 0), int(profile_max_turns or 0), _MIN_CHILD_TURNS),
        cap,
    )


def child_session_id_for(envelope: Any) -> str:
    """The child session id a handoff creates (so a caller can link to the child conversation) [CARD-563]."""
    return f"{envelope.session_id}{CHILD_SESSION_MARKER}{envelope.correlation_id[:8]}"


def infer_handoff_depth(session_id: str) -> int:
    """Chat is tier 1. Each _child_ marker already in the session adds a tier."""
    return (session_id or "").count(CHILD_SESSION_MARKER) + 1


def parent_session_id_from_child(child_session_id: str) -> Optional[str]:
    sid = child_session_id or ""
    if CHILD_SESSION_MARKER not in sid:
        return None
    return sid.rsplit(CHILD_SESSION_MARKER, 1)[0]


def parse_parked_payload(text: str) -> Optional[dict]:
    try:
        parsed = json.loads(text or "")
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, dict) and parsed.get("status") == "approval_required" and parsed.get("approval_id"):
        return parsed
    return None


def is_handoff_child_session(session_id: str) -> bool:
    return CHILD_SESSION_MARKER in (session_id or "")


def resolve_handoff_packet(envelope: HandoffEnvelope) -> HandoffPacket:
    """Require a complete packet. Map legacy task_intent+context_payload so old callers do not crash."""
    if envelope.packet is not None:
        packet = envelope.packet
        if not (packet.goal or "").strip() or not (packet.done_when or "").strip():
            raise HandoffPacketError("HandoffPacket requires goal, facts, constraints, done_when, and budget.")
        return packet
    try:
        return HandoffPacket.from_legacy_envelope(
            task_intent=envelope.task_intent,
            context_payload=envelope.context_payload,
            max_turns=envelope.max_turns,
        )
    except Exception as exc:
        raise HandoffPacketError(f"HandoffPacket requires goal, facts, constraints, done_when, and budget: {exc}") from exc


async def _call_kernel_turn(fn, kwargs):
    """Invoke run_turn/execute_turn without breaking kernels that lack approval_mode."""
    call_kwargs = dict(kwargs)
    try:
        sig = inspect.signature(fn)
        params = sig.parameters
        accepts_var = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if "approval_mode" not in params and not accepts_var:
            call_kwargs.pop("approval_mode", None)
    except (TypeError, ValueError):
        pass
    return await fn(**call_kwargs)


async def _iter_kernel_stream(fn, kwargs) -> AsyncIterator[Any]:
    """Invoke stream_turn, dropping kwargs the kernel does not accept."""
    call_kwargs = dict(kwargs)
    try:
        sig = inspect.signature(fn)
        params = sig.parameters
        accepts_var = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if not accepts_var:
            call_kwargs = {k: v for k, v in call_kwargs.items() if k in params}
    except (TypeError, ValueError):
        pass
    agen = fn(**call_kwargs)
    if inspect.iscoroutine(agen):
        await agen
        raise TypeError("stream_turn must be an async generator, not a coroutine")
    async for ev in agen:
        yield ev


CHILD_CONTINUE_NUDGE = "Your last reply was empty. Continue the task from where you stopped."
CHILD_MALFORMED_NUDGE = (
    "Your last reply could not be read (the provider could not parse the tool call). Continue the task from where you "
    "stopped, one tool call at a time."
)
# CARD-564: the model's tool call was malformed and the provider failed to parse it (seen on Nimo/Ollama:
# "XML syntax error ... element <function> closed by </parameter>"). One sampling flake, like an empty reply.
_MALFORMED_TOOL_CALL = re.compile(r"stream error:.*(xml syntax error|failed to parse|error parsing tool call)", re.I)


def _is_empty_reply_error(ev: Any) -> bool:
    from src.application.kernel.empty_reply import EMPTY_REPLY_MESSAGE

    ev_type = getattr(ev, "event_type", None)
    return getattr(ev_type, "value", ev_type) == "error" and str(getattr(ev, "content", "") or "") == EMPTY_REPLY_MESSAGE


def _retry_nudge(ev: Any) -> str:
    """The nudge for a child error worth one retry (empty reply, malformed tool call), or ''."""
    if _is_empty_reply_error(ev):
        return CHILD_CONTINUE_NUDGE
    ev_type = getattr(ev, "event_type", None)
    if getattr(ev_type, "value", ev_type) == "error" and _MALFORMED_TOOL_CALL.search(str(getattr(ev, "content", "") or "")):
        return CHILD_MALFORMED_NUDGE
    return ""


async def _stream_with_empty_retry(fn, kwargs) -> AsyncIterator[Any]:
    """A child turn that ends in an empty model reply (CARD-563) or a tool call the provider could not parse
    (CARD-564) is nudged once to continue; one flake no longer ends a whole card run. A second one is passed on."""
    kw = dict(kwargs)
    for attempt in range(2):
        nudge = ""
        async for ev in _iter_kernel_stream(fn, kw):
            if attempt == 0 and not nudge:
                nudge = _retry_nudge(ev)
                if nudge:
                    continue
            if nudge and attempt == 0:
                continue  # nothing useful follows the error in this attempt
            yield ev
        if not nudge:
            return
        logger.info("Child %s hit a retryable model flake; nudging it to continue once", kw.get("session_id"))
        kw = {**kw, "user_content": nudge, "resume": False}


class HandoffIsolationEngine:
    """
    Executes subagent handoffs within isolated conversation contexts,
    enforcing anti-recursion and turn-bounded safety guards.
    """

    def __init__(
        self,
        agent_registry: Any,
        state_store: SQLiteStateStore,
        kernel: Optional[Any] = None,
        kernel_factory: Optional[Callable[[AgentProfile], Any]] = None,
        telemetry: Optional[Any] = None,
        job_orchestrator: Optional[Any] = None,
    ):
        self.agent_registry = agent_registry
        self.state_store = state_store
        self.kernel = kernel
        self.kernel_factory = kernel_factory
        self.telemetry = telemetry
        self.job_orchestrator = job_orchestrator
        # CARD-563: parent tool name -> fn(tool arguments, child_session_id) -> extra outcome text on completion.
        self.parent_tool_outcomes: dict[str, Callable[[dict, str], str]] = {}

    async def execute_handoff(
        self,
        envelope: HandoffEnvelope,
        on_event: Optional[Callable[[str, Any], None]] = None,
    ) -> HandoffResult:
        """
        Execute an isolated child session for the recipient specialist agent.
        Child uses stream_turn with the packet as the only user message [REQ-ORCH-037].
        """
        import time

        start_time = time.perf_counter()
        parent_job_id = None
        child_job_id = None
        same_job_id = None

        def _record_span(res: HandoffResult) -> HandoffResult:
            # Stamp standing A2A link ids when present [CARD-224 / CARD-265].
            if parent_job_id and not res.parent_job_id:
                res.parent_job_id = parent_job_id
            if child_job_id and not res.child_job_id:
                res.child_job_id = child_job_id
            if same_job_id and not getattr(res, "same_job_id", None):
                res.same_job_id = same_job_id
            telem = self.telemetry or getattr(self.kernel, "telemetry", None)
            if telem and hasattr(telem, "record_handoff_span"):
                dur_ms = (time.perf_counter() - start_time) * 1000
                telem.record_handoff_span(
                    sender_agent_id=envelope.sender_agent_id,
                    recipient_agent_id=envelope.recipient_agent_id,
                    session_id=envelope.session_id,
                    correlation_id=envelope.correlation_id,
                    duration_ms=dur_ms,
                    success=(res.status in ("completed", "approval_required")),
                    status="hitl_paused" if res.status == "approval_required" else res.status,
                    error_message=res.error_message,
                    trace_id=envelope.session_id,
                )
            return res

        # 1. Guardrail: Anti-Recursion Depth Check (Max 2 tiers)
        if envelope.depth > 2:
            logger.warning(
                "Rejected handoff %s: Depth %d exceeds max allowed depth 2",
                envelope.correlation_id,
                envelope.depth,
            )
            return _record_span(
                HandoffResult(
                    correlation_id=envelope.correlation_id,
                    sender_agent_id=envelope.sender_agent_id,
                    recipient_agent_id=envelope.recipient_agent_id,
                    status="rejected",
                    summary="",
                    error_message="Recursion depth limit exceeded (max depth: 2).",
                )
            )

        recipient_id = canonical_agent_id(envelope.recipient_agent_id)
        sender_id = canonical_agent_id(envelope.sender_agent_id)

        # 2. Guardrail: Circular Self-Handoff Check
        if recipient_id == sender_id or envelope.recipient_agent_id == envelope.sender_agent_id:
            logger.warning(
                "Rejected self-handoff from agent '%s'",
                envelope.sender_agent_id,
            )
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="rejected",
                summary="",
                error_message="Self-handoff is forbidden to prevent circular deadlocks.",
            )

        # 3. Target Specialist Profile Resolution
        target_profile = self.agent_registry.get_agent(recipient_id) or self.agent_registry.get_profile(recipient_id)
        if not target_profile:
            logger.error("Recipient agent '%s' not found in registry", envelope.recipient_agent_id)
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="failed",
                summary="",
                error_message=f"Specialist agent '{envelope.recipient_agent_id}' not found in registry.",
            )

        try:
            packet = resolve_handoff_packet(envelope)
        except HandoffPacketError as exc:
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="failed",
                summary="",
                error_message=str(exc),
            )

        # Standing A2A inherit [CARD-224 / CARD-265]:
        # Default = same job_id tree (265). Opt-in linked_child_job=true keeps 224 child.
        payload = dict(envelope.context_payload or {})
        parent_job_id = (
            str(payload.get("parent_job_id") or payload.get("job_id") or "").strip() or None
        )
        want_linked_child = bool(payload.get("linked_child_job"))
        if parent_job_id and self.job_orchestrator is not None:
            try:
                if want_linked_child:
                    from src.application.orchestration.standing_a2a_handoff import (
                        create_standing_child_job,
                    )

                    child_job = create_standing_child_job(
                        self.job_orchestrator,
                        parent_job_id=parent_job_id,
                        intent=packet.goal or envelope.task_intent,
                        session_id=envelope.session_id,
                        agent_id=recipient_id,
                        role=recipient_id,
                        verify_checker=None,
                    )
                    child_job_id = child_job.id
                    payload["child_job_id"] = child_job_id
                    payload["parent_job_id"] = parent_job_id
                    payload["same_job_id"] = None
                    envelope.context_payload = payload
                else:
                    from src.application.orchestration.standing_a2a_handoff import (
                        bind_specialist_same_job,
                    )

                    bound = bind_specialist_same_job(
                        self.job_orchestrator,
                        job_id=parent_job_id,
                        specialist_agent_id=recipient_id,
                        specialty=packet.goal or envelope.task_intent,
                        # CARD-554: the handoff runs inside the parent's turn, which then completes its phase; parking
                        # the running phase made that completion fail ("another run of this job changed this step").
                        park=bool(payload.get("park_on_handoff", False)),
                    )
                    same_job_id = str(bound.get("same_job_id") or parent_job_id)
                    child_job_id = same_job_id  # bind turn to same tree
                    payload["parent_job_id"] = parent_job_id
                    payload["child_job_id"] = same_job_id
                    payload["same_job_id"] = same_job_id
                    payload["privilege_escalated"] = False
                    envelope.context_payload = payload
            except Exception as exc:  # noqa: BLE001 — handoff continues; standing link best-effort
                logger.warning(
                    "Standing A2A same-job/child bind failed for parent %s: %s",
                    parent_job_id,
                    exc,
                )

        child_prompt = packet.render_user_message()

        # 4. Create Isolated Child Session ID from the live parent session
        child_session_id = child_session_id_for(envelope)
        if self.state_store and hasattr(self.state_store, "create_session"):
            try:
                self.state_store.create_session(
                    session_id=child_session_id,
                    agent_id=recipient_id,
                    title=str(payload.get("child_session_title") or f"Handoff: {packet.goal[:30]}"),
                )
            except Exception:
                pass

        # 5. Resolve Execution Kernel
        exec_kernel = self.kernel_factory(target_profile) if self.kernel_factory else self.kernel

        if not exec_kernel:
            return HandoffResult(
                correlation_id=envelope.correlation_id,
                sender_agent_id=envelope.sender_agent_id,
                recipient_agent_id=envelope.recipient_agent_id,
                status="failed",
                summary="",
                error_message="Execution kernel unavailable for handoff execution.",
            )

        # 6. Bound Turns - at least 10 (or the specialist profile), cap 15.
        bounded_profile = target_profile.model_copy()
        bounded_profile.max_turns = bound_child_max_turns(
            envelope.max_turns,
            getattr(target_profile, "max_turns", DEFAULT_AGENT_MAX_TURNS) or DEFAULT_AGENT_MAX_TURNS,
            cap=_MAX_CARD_HANDOFF_TURNS if payload.get("card_handoff") else _MAX_CHILD_TURNS,
        )

        if on_event:
            on_event(
                "handoff_start",
                {
                    "correlation_id": envelope.correlation_id,
                    "sender": envelope.sender_agent_id,
                    "recipient": envelope.recipient_agent_id,
                    "recipient_name": target_profile.name,
                    "directive": packet.goal,
                },
            )

        try:
            stream_fn = getattr(exec_kernel, "stream_turn", None)
            if not callable(stream_fn):
                raise AttributeError("Execution kernel does not implement stream_turn")

            turn_kwargs = {
                "agent": bounded_profile,
                "session_id": child_session_id,
                "user_content": child_prompt,
                "approval_mode": getattr(envelope, "approval_mode", "ask") or "ask",
            }
            # Bind standing job (same-tree 265 or linked child 224) for CARD-221 matched IDs.
            if child_job_id:
                turn_kwargs["job_id"] = child_job_id

            summary_parts: list[str] = []
            last_content = ""
            parked = None
            error_text = None
            turns_taken = 1

            async for ev in _stream_with_empty_retry(stream_fn, turn_kwargs):
                ev_type = getattr(ev, "event_type", None)
                ev_val = getattr(ev_type, "value", ev_type)
                if on_event and ev_val not in ("handoff_start", "handoff_complete"):
                    on_event(
                        str(ev_val),
                        {
                            "correlation_id": envelope.correlation_id,
                            "content": getattr(ev, "content", None),
                            "react": getattr(ev, "react", None),
                        },
                    )
                if ev_val in (KernelEventType.TOKEN, "token") and getattr(ev, "content", None):
                    summary_parts.append(str(ev.content))
                react = getattr(ev, "react", None)
                if isinstance(react, dict) and isinstance(react.get("turn_idx"), int):
                    # CARD-523: count the child's real steps (the limit stop reports turn_idx == max_turns).
                    turns_taken = max(turns_taken, min(react["turn_idx"] + 1, bounded_profile.max_turns))
                if ev_val in (KernelEventType.ERROR, "error"):
                    error_text = str(getattr(ev, "content", "") or "")
                if ev_val in (KernelEventType.APPROVAL_REQUIRED, "approval_required"):
                    tool_call = getattr(ev, "tool_call", None) or {}
                    parked = {
                        "status": "approval_required",
                        "approval_id": getattr(ev, "approval_id", None),
                        "tool_name": tool_call.get("name") if isinstance(tool_call, dict) else None,
                        "arguments": tool_call.get("arguments") if isinstance(tool_call, dict) else {},
                        "message": getattr(ev, "content", None) or "Approval required",
                    }
                if getattr(ev, "is_finished", False):
                    last_content = str(getattr(ev, "content", "") or last_content)

            summary_text = "".join(summary_parts) or last_content
            if not parked:
                parked = parse_parked_payload(summary_text)

            if parked:
                if on_event:
                    on_event(
                        "handoff_complete",
                        {
                            "correlation_id": envelope.correlation_id,
                            "recipient": envelope.recipient_agent_id,
                            "recipient_name": target_profile.name,
                            "status": "approval_required",
                            "turns_used": turns_taken,
                        },
                    )
                return _record_span(
                    HandoffResult(
                        correlation_id=envelope.correlation_id,
                        sender_agent_id=envelope.sender_agent_id,
                        recipient_agent_id=envelope.recipient_agent_id,
                        status="approval_required",
                        summary=str(parked.get("message") or "Specialist parked a tool for approval."),
                        turns_used=turns_taken,
                        error_message=str(parked.get("message") or "Approval required"),
                        approval_id=str(parked.get("approval_id")),
                        parked_tool_name=parked.get("tool_name"),
                        parked_arguments=parked.get("arguments") if isinstance(parked.get("arguments"), dict) else {},
                    )
                )

            failure_blob = error_text or summary_text
            if error_text or looks_like_provider_failure(failure_blob):
                if on_event:
                    on_event(
                        "handoff_complete",
                        {
                            "correlation_id": envelope.correlation_id,
                            "recipient": envelope.recipient_agent_id,
                            "recipient_name": target_profile.name,
                            "status": "failed",
                            "turns_used": turns_taken,
                            "error": failure_blob,
                        },
                    )
                return _record_span(
                    HandoffResult(
                        correlation_id=envelope.correlation_id,
                        sender_agent_id=envelope.sender_agent_id,
                        recipient_agent_id=envelope.recipient_agent_id,
                        status="failed",
                        summary=summary_text,
                        turns_used=turns_taken,
                        error_message=failure_blob,
                    )
                )

            from src.application.kernel.turn_limit import is_turn_limit_reply  # local: kernel imports this module

            final_status = "incomplete" if is_turn_limit_reply(summary_text) else "completed"
            if on_event:
                on_event(
                    "handoff_complete",
                    {
                        "correlation_id": envelope.correlation_id,
                        "recipient": envelope.recipient_agent_id,
                        "recipient_name": target_profile.name,
                        "status": final_status,
                        "turns_used": turns_taken,
                    },
                )

            return _record_span(
                HandoffResult(
                    correlation_id=envelope.correlation_id,
                    sender_agent_id=envelope.sender_agent_id,
                    recipient_agent_id=envelope.recipient_agent_id,
                    status=final_status,
                    summary=summary_text,
                    turns_used=turns_taken,
                )
            )

        except Exception as err:
            logger.error("Handoff execution failed for %s: %s", envelope.correlation_id, err, exc_info=True)
            if on_event:
                on_event(
                    "handoff_complete",
                    {
                        "correlation_id": envelope.correlation_id,
                        "recipient": envelope.recipient_agent_id,
                        "status": "failed",
                        "error": str(err),
                    },
                )
            return _record_span(
                HandoffResult(
                    correlation_id=envelope.correlation_id,
                    sender_agent_id=envelope.sender_agent_id,
                    recipient_agent_id=envelope.recipient_agent_id,
                    status="failed",
                    summary="",
                    error_message=f"Subagent execution error: {str(err)}",
                )
            )

    async def resume_nested_child(
        self,
        child_session_id: str,
        parent_session_id: Optional[str] = None,
        approval_mode: str = "ask",
        agent_id: Optional[str] = None,
    ) -> dict:
        """
        Continue a parked child ReAct loop, then write the result onto the parent
        handoff TOOL row [REQ-HITL-036] [REQ-HITL-037].
        """
        parent_id = parent_session_id or parent_session_id_from_child(child_session_id)
        child_sess = None
        if self.state_store and hasattr(self.state_store, "get_session"):
            try:
                child_sess = self.state_store.get_session(child_session_id)
            except Exception:
                child_sess = None
        resolved_agent_id = agent_id or (getattr(child_sess, "agent_id", None) if child_sess else None)
        profile = None
        if resolved_agent_id:
            profile = self.agent_registry.get_agent(resolved_agent_id) or self.agent_registry.get_profile(resolved_agent_id)
        exec_kernel = self.kernel
        if not exec_kernel or not profile:
            return {"status": "skipped", "reason": "kernel or child profile unavailable"}

        parked = None
        summary = ""
        child_error = ""
        try:
            if hasattr(exec_kernel, "stream_turn"):
                resume_kwargs = {
                    "agent": profile,
                    "session_id": child_session_id,
                    "user_content": None,
                    "approval_mode": approval_mode or "ask",
                    "resume": True,
                }
                async for ev in _stream_with_empty_retry(exec_kernel.stream_turn, resume_kwargs):
                    ev_type = getattr(ev, "event_type", None)
                    if getattr(ev_type, "value", ev_type) == "error":
                        child_error = str(getattr(ev, "content", "") or "error")
                    if ev_type == KernelEventType.APPROVAL_REQUIRED or getattr(ev_type, "value", ev_type) == "approval_required":
                        tool_call = getattr(ev, "tool_call", None) or {}
                        parked = {
                            "status": "approval_required",
                            "approval_id": getattr(ev, "approval_id", None),
                            "tool_name": tool_call.get("name") if isinstance(tool_call, dict) else None,
                            "arguments": tool_call.get("arguments") if isinstance(tool_call, dict) else {},
                            "message": getattr(ev, "content", None) or "Approval required",
                        }
                    if getattr(ev, "is_finished", False):
                        summary = str(getattr(ev, "content", "") or summary)
            elif hasattr(exec_kernel, "run_turn"):
                result = await _call_kernel_turn(
                    exec_kernel.run_turn,
                    {
                        "agent": profile,
                        "session_id": child_session_id,
                        "user_content": None,
                        "approval_mode": approval_mode or "ask",
                    },
                )
                summary = str(getattr(result, "content", None) or result)
                parked = parse_parked_payload(summary)
            else:
                return {"status": "skipped", "reason": "kernel has no stream_turn or run_turn"}
        except Exception as err:
            logger.error("Nested child resume failed for %s: %s", child_session_id, err, exc_info=True)
            summary = f"Specialist resume failed: {err}"
            self._write_parent_handoff_tool(
                parent_id=parent_id,
                agent_id=profile.id,
                content=(
                    f"=== Subagent Handoff Failed ({profile.id}) ===\n"
                    f"Error: {summary}"
                ),
            )
            return {"status": "failed", "summary": summary}

        if parked:
            payload = {
                "status": "approval_required",
                "approval_id": parked.get("approval_id"),
                "tool_name": parked.get("tool_name") or "tool",
                "arguments": parked.get("arguments") if isinstance(parked.get("arguments"), dict) else {},
                "message": parked.get("message") or "Approval required",
                "recipient_agent_id": profile.id,
            }
            self._write_parent_handoff_tool(
                parent_id=parent_id,
                agent_id=profile.id,
                content=json.dumps(payload),
            )
            return {"status": "approval_required", "parked": payload, "summary": payload["message"]}

        status = "failed" if child_error else "completed"
        content = (
            f"=== Subagent Handoff {'Failed' if child_error else 'Completed'} ({profile.id}) ===\n"
            f"Status: {status}\n"
            f"Conclusion:\n{child_error or summary}"
        )
        _tcid, parent_tool, parent_args = self._parent_handoff_call(parent_id)
        hook = self.parent_tool_outcomes.get(parent_tool or "")
        if hook is not None:
            try:  # CARD-563: the outcome is read from git and the card, not the child's claim
                tail = f"Developer stopped with an error: {child_error}" if child_error else f"Developer's own summary:\n{summary}"
                content = hook(parent_args, child_session_id) + "\n\n" + tail
            except Exception:
                logger.exception("Parent outcome hook failed for %s", parent_tool)
        self._write_parent_handoff_tool(parent_id=parent_id, agent_id=profile.id, content=content)
        return {"status": status, "summary": child_error or summary}

    def _parent_handoff_call(self, parent_id: Optional[str]) -> tuple[Optional[str], Optional[str], dict]:
        """(tool_call_id, tool name, arguments) of the parent's latest handoff tool call."""
        if not parent_id or not self.state_store or not hasattr(self.state_store, "get_messages"):
            return None, None, {}
        try:
            for pm in reversed(self.state_store.get_messages(parent_id)):
                if pm.role == Role.ASSISTANT and pm.tool_calls:
                    for tc in pm.tool_calls:
                        if tc.name in PARENT_HANDOFF_TOOLS:
                            return tc.id, tc.name, tc.arguments if isinstance(tc.arguments, dict) else {}
        except Exception:
            return None, None, {}
        return None, None, {}

    def _write_parent_handoff_tool(
        self,
        parent_id: Optional[str],
        agent_id: str,
        content: str,
        tool_call_id: Optional[str] = None,
    ) -> None:
        if not parent_id or not self.state_store:
            return
        found_id, found_name, _args = self._parent_handoff_call(parent_id)
        resolved_tcid = tool_call_id or found_id

        try:
            self.state_store.save_message(
                session_id=parent_id,
                agent_id=agent_id,
                message=ChatMessage(
                    role=Role.TOOL,
                    content=content,
                    name=found_name or "handoff_to_agent",
                    tool_call_id=resolved_tcid,
                ),
            )
        except Exception:
            logger.exception("Failed to write parent handoff TOOL for %s", parent_id)
