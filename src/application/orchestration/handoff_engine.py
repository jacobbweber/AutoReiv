"""
Isolated Subagent Handoff Execution Engine [REQ-ORCH-003].
Orchestrates isolated child execution loops with recursion depth & turn bounding.
Child path uses stream_turn with a HandoffPacket user message [REQ-ORCH-036, REQ-ORCH-037].
"""

import inspect
import json
import logging
from typing import Any, AsyncIterator, Callable, Optional

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.domain.orchestration.errors import HandoffPacketError
from src.domain.orchestration.models import HandoffEnvelope, HandoffPacket, HandoffResult
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

logger = logging.getLogger(__name__)

CHILD_SESSION_MARKER = "_child_"
_MIN_CHILD_TURNS = 10
_MAX_CHILD_TURNS = 15
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


def bound_child_max_turns(envelope_max_turns: int, profile_max_turns: int) -> int:
    """Child turn budget: at least 10 (or the profile), never above 15."""
    return min(
        max(int(envelope_max_turns or 0), int(profile_max_turns or 0), _MIN_CHILD_TURNS),
        _MAX_CHILD_TURNS,
    )


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
    ):
        self.agent_registry = agent_registry
        self.state_store = state_store
        self.kernel = kernel
        self.kernel_factory = kernel_factory
        self.telemetry = telemetry

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

        def _record_span(res: HandoffResult) -> HandoffResult:
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

        alias_map = {
            "sysadmin": "autoreiv",
            "linux-sysadmin": "autoreiv",
            "system-agent": "autoreiv",
            "system": "autoreiv",
            "librarian": "assistant",
            "system-librarian": "assistant",
            "general-assistant": "assistant",
            "general": "assistant",
        }
        recipient_id = alias_map.get(envelope.recipient_agent_id, envelope.recipient_agent_id)
        sender_id = alias_map.get(envelope.sender_agent_id, envelope.sender_agent_id)

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

        child_prompt = packet.render_user_message()

        # 4. Create Isolated Child Session ID from the live parent session
        child_session_id = f"{envelope.session_id}{CHILD_SESSION_MARKER}{envelope.correlation_id[:8]}"
        if self.state_store and hasattr(self.state_store, "create_session"):
            try:
                self.state_store.create_session(
                    session_id=child_session_id,
                    agent_id=recipient_id,
                    title=f"Handoff: {packet.goal[:30]}",
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
            envelope.max_turns, getattr(target_profile, "max_turns", 10) or 10
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

            summary_parts: list[str] = []
            last_content = ""
            parked = None
            error_text = None
            turns_taken = 1

            async for ev in _iter_kernel_stream(stream_fn, turn_kwargs):
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

            if on_event:
                on_event(
                    "handoff_complete",
                    {
                        "correlation_id": envelope.correlation_id,
                        "recipient": envelope.recipient_agent_id,
                        "recipient_name": target_profile.name,
                        "status": "completed",
                        "turns_used": turns_taken,
                    },
                )

            return _record_span(
                HandoffResult(
                    correlation_id=envelope.correlation_id,
                    sender_agent_id=envelope.sender_agent_id,
                    recipient_agent_id=envelope.recipient_agent_id,
                    status="completed",
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
        try:
            if hasattr(exec_kernel, "stream_turn"):
                async for ev in exec_kernel.stream_turn(
                    agent=profile,
                    session_id=child_session_id,
                    user_content=None,
                    approval_mode=approval_mode or "ask",
                    resume=True,
                ):
                    ev_type = getattr(ev, "event_type", None)
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

        content = (
            f"=== Subagent Handoff Completed ({profile.id}) ===\n"
            f"Status: completed\n"
            f"Conclusion:\n{summary}"
        )
        self._write_parent_handoff_tool(parent_id=parent_id, agent_id=profile.id, content=content)
        return {"status": "completed", "summary": summary}

    def _write_parent_handoff_tool(self, parent_id: Optional[str], agent_id: str, content: str) -> None:
        if not parent_id or not self.state_store:
            return
        try:
            self.state_store.save_message(
                session_id=parent_id,
                agent_id=agent_id,
                message=ChatMessage(
                    role=Role.TOOL,
                    content=content,
                    name="handoff_to_agent",
                ),
            )
        except Exception:
            logger.exception("Failed to write parent handoff TOOL for %s", parent_id)
