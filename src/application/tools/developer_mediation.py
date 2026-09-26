"""Tools Studio developer-mediated tool intent [CARD-422 / ADR-0057].

Talk opens a new developer chat that already contains the form context.
Submit starts a standing job and runs one developer turn on that chat.
A queued job with no turn is not success. Packaging preference stays a note
on this packet. CARD-423 lanes are built by the developer, not by this form.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Mapping, Optional

from src.application.orchestration.chat_job_binding import output_packet_for_phase
from src.application.orchestration.phase_llm_resilience import resolve_standing_phase_llm_timeout
from src.application.tools.tool_check import tool_checks_for_job
from src.domain.gateway.models import ChatMessage, Role
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseSpec, PhaseStatus

logger = logging.getLogger(__name__)

PACKET_SCHEMA = "tools_studio_authoring_packet"
PACKET_VERSION = 1
TEMPLATE_ID = "tools_studio_developer_mediation"
DEVELOPER_AGENT_ID = "developer"
PACKET_EVENT_KIND = "tools_studio_authoring_packet"
TURN_EVENT_KIND = "tools_studio_developer_turn"
PACKET_FACT_PREFIX = "tools_studio_authoring_packet_json="
INTENTS = frozenset({"create", "modify", "delete"})
PACKAGING_PREFERENCES = frozenset({"", "native", "mcp"})
MATCHED_CAPABILITY_ID = "skill.sdlc-engineering"
SUCCESS_RULE = "done when: the developer has replied in this chat to the Tools Studio tool intent."
_CODE_KEYS = ("code", "implementation", "source_code", "script")
_OPEN_FAILURE = frozenset({JobStatus.QUEUED.value, PhaseStatus.QUEUED.value})


class ToolsAuthoringError(ValueError):
    def __init__(self, message: str, status_code: int = 400, **extra: Any):
        super().__init__(message)
        self.status_code = status_code
        self.extra = extra


def _status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status or "")


def _role_value(message: Any) -> str:
    role = getattr(message, "role", "")
    return role.value if hasattr(role, "value") else str(role or "")


def normalize_tool_draft(raw: Optional[Mapping[str, Any]], intent: str) -> dict[str, Any]:
    source = dict(raw or {})
    for key in _CODE_KEYS:
        if str(source.get(key) or "").strip():
            raise ToolsAuthoringError(
                "Tools Studio does not accept tool implementation code. Describe what the tool should do."
            )
    clean_intent = str(intent or source.get("intent") or "").strip().lower()
    if clean_intent not in INTENTS:
        raise ToolsAuthoringError("intent must be create, modify, or delete")
    packaging = str(source.get("packaging_preference") or "").strip().lower()
    if packaging not in PACKAGING_PREFERENCES:
        raise ToolsAuthoringError("packaging_preference must be empty, native, or mcp")
    draft = {
        "tool_name": str(source.get("tool_name") or "").strip(),
        "behavior": str(source.get("behavior") or "").strip(),
        "language_hint": str(source.get("language_hint") or "").strip(),
        "runtime_hint": str(source.get("runtime_hint") or "").strip(),
        "path_context": str(source.get("path_context") or "").strip(),
        "packaging_preference": packaging,
    }
    if clean_intent in {"modify", "delete"} and not draft["tool_name"]:
        raise ToolsAuthoringError("tool_name is required for modify and delete")
    if clean_intent in {"create", "modify"} and not draft["behavior"]:
        raise ToolsAuthoringError("behavior is required for create and modify")
    if clean_intent == "delete" and not draft["behavior"]:
        draft["behavior"] = f"Remove the custom tool {draft['tool_name']}."
    return draft


def build_packet(intent: str, draft: Mapping[str, Any]) -> dict[str, Any]:
    clean_intent = str(intent or "").strip().lower()
    normalized = normalize_tool_draft(draft, clean_intent)
    return {
        "schema": PACKET_SCHEMA,
        "version": PACKET_VERSION,
        "studio": "tools",
        "intent": clean_intent,
        "agent_id": DEVELOPER_AGENT_ID,
        "draft": normalized,
        "llm_rewrite": False,
        "packaging_applied": False,
    }


def format_developer_prompt(packet: Mapping[str, Any]) -> str:
    draft = packet.get("draft") if isinstance(packet.get("draft"), Mapping) else {}
    packaging = str(draft.get("packaging_preference") or "").strip() or "unspecified"
    tool_name = str(draft.get("tool_name") or "").strip() or "(new tool)"
    return (
        f"Tools Studio tool intent ({packet.get('intent')}).\n\n"
        f"Tool name: {tool_name}\n"
        f"What it should do: {draft.get('behavior') or ''}\n"
        f"Language hint: {draft.get('language_hint') or 'none'}\n"
        f"Runtime hint: {draft.get('runtime_hint') or 'none'}\n"
        f"Path or context: {draft.get('path_context') or 'none'}\n"
        f"Packaging preference (note only, not a completed package): {packaging}\n\n"
        "Both lanes exist. Native: register_native_tool in native-tool-engineering (no MCP server). "
        "MCP: mcp-engineering, then attach; Tools Studio groups tools under that server name. "
        "A filesystem path in this message is developer chat context, not a Tools Studio folder picker.\n\n"
        "Registering runs the tool once in the sandbox first (register_native_tool or register_mcp_service). "
        "Pass harmless sample_arguments; use sample_call skip with skip_reason only for secrets, network or side effects. "
        "If the result says Not registered, nothing was saved: tell the operator the error, fix it, and register again.\n\n"
        "Reply in this chat with the next concrete step. "
        "Tools Studio did not include implementation code and did not write a tool file."
    )


def _session_title(packet: Mapping[str, Any]) -> str:
    draft = packet.get("draft") if isinstance(packet.get("draft"), Mapping) else {}
    name = str(draft.get("tool_name") or "").strip() or "new tool"
    return f"Tools Studio {packet.get('intent')}: {name}"[:80]


def _prefixed_json(payload: Mapping[str, Any]) -> str:
    return PACKET_FACT_PREFIX + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _handoff_json(goal: str, payload_fact: str) -> str:
    packet = HandoffPacket(
        goal=goal,
        facts=[payload_fact],
        constraints=[
            "Reply in the developer chat. Do not assume Tools Studio wrote code.",
            "packaging_preference is a note only. Do not treat native or MCP packaging as applied.",
        ],
        done_when=SUCCESS_RULE,
        budget={"max_turns": 8, "max_handoffs": 1, "max_ollama_slots": 1},
    )
    return packet.model_dump_json()


def _load_packet(raw_json: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw_json:
        return None
    try:
        packet = HandoffPacket.model_validate_json(raw_json)
    except Exception:
        return None
    for fact in packet.facts:
        if str(fact).startswith(PACKET_FACT_PREFIX):
            try:
                loaded = json.loads(str(fact)[len(PACKET_FACT_PREFIX) :])
            except json.JSONDecodeError:
                return None
            return loaded if isinstance(loaded, dict) else None
    return None


class ToolsDeveloperMediationService:
    def __init__(self, store: Any, orchestrator: Any, registry: Any = None, kernel: Any = None) -> None:
        self._store = store
        self._orchestrator = orchestrator
        self._registry = registry
        self._kernel = kernel

    def open_chat(self, intent: str, draft: Optional[Mapping[str, Any]]) -> dict[str, Any]:
        """New, empty developer session plus the prompt. No job.

        The browser sends ``prompt`` as a real turn via /api/chat/stream so the Developer replies at once
        (CARD-497 REQ-497-016); pre-saving it here left a message that looked sent but never ran.
        """
        self._require_store()
        self._require_developer()
        packet = build_packet(intent, draft or {})
        prompt = format_developer_prompt(packet)
        session = self._store.create_session(agent_id=DEVELOPER_AGENT_ID, title=_session_title(packet))
        logger.info("Tools Studio opened developer chat %s for %s", session.id, packet["intent"])
        return {
            "session_id": session.id,
            "agent_id": DEVELOPER_AGENT_ID,
            "title": session.title,
            "prompt": prompt,
            "opened_chat": True,
            "opened_job": False,
            "job_id": None,
            "packet": packet,
            "persisted_tool": False,
            "packaging_applied": False,
        }

    async def submit(self, intent: str, draft: Optional[Mapping[str, Any]]) -> dict[str, Any]:
        """Create a standing job and run one developer turn. Refuse if that cannot happen."""
        self._require_store()
        self._require_developer()
        self._require_orchestrator()
        kernel = self._require_kernel()
        packet = build_packet(intent, draft or {})
        prompt = format_developer_prompt(packet)
        session = self._store.create_session(agent_id=DEVELOPER_AGENT_ID, title=_session_title(packet))
        self._store.save_message(
            session_id=session.id,
            agent_id=DEVELOPER_AGENT_ID,
            message=ChatMessage(role=Role.USER, content=prompt),
        )
        job = self._create_job(packet, session.id)
        self._stamp_packet(job, packet)
        self._seed_intake(job)
        phase = self._author_phase(job.id)
        try:
            started = self._orchestrator.start_phase(phase.id)
        except Exception as exc:
            closed = self._close_failed(job.id, phase.id, f"mediation_start_failed: {exc}")
            raise ToolsAuthoringError(
                f"Developer mediation could not start: {exc}",
                503,
                job_id=job.id,
                session_id=session.id,
                status=closed,
                ran=False,
            ) from exc
        try:
            reply = await asyncio.wait_for(
                kernel.run_turn(
                    agent=self._require_developer(),
                    session_id=session.id,
                    user_content=None,
                    save_to_history=False,
                    resume=True,
                    approval_mode="ask",
                    job_id=job.id,
                    phase_id=started.id,
                ),
                timeout=resolve_standing_phase_llm_timeout(),
            )
        except asyncio.TimeoutError as exc:
            closed = self._close_failed(job.id, started.id, "developer_turn_timeout")
            raise ToolsAuthoringError(
                "Developer mediation timed out before the developer replied.",
                503,
                job_id=job.id,
                session_id=session.id,
                status=closed,
                ran=False,
            ) from exc
        except Exception as exc:
            closed = self._close_failed(job.id, started.id, f"developer_turn_failed: {exc}")
            raise ToolsAuthoringError(
                f"Developer mediation did not run: {exc}",
                503,
                job_id=job.id,
                session_id=session.id,
                status=closed,
                ran=False,
            ) from exc
        text = str(getattr(reply, "content", "") or "").strip()
        if not text:
            closed = self._close_failed(job.id, started.id, "developer_turn_empty")
            raise ToolsAuthoringError(
                "Developer mediation returned an empty reply.",
                503,
                job_id=job.id,
                session_id=session.id,
                status=closed,
                ran=False,
            )
        self._ensure_assistant_message(session.id, text)
        status = self._finish_phase(job.id, started.id, session.id, text)
        if status in _OPEN_FAILURE or status == JobStatus.QUEUED.value:
            raise ToolsAuthoringError(
                "Developer mediation did not leave the queue.",
                503,
                job_id=job.id,
                session_id=session.id,
                status=status,
                ran=False,
            )
        self._record_event(
            job.id,
            TURN_EVENT_KIND,
            {
                "session_id": session.id,
                "status": status,
                "reply_chars": len(text),
                "ran": True,
            },
        )
        logger.info("Tools Studio developer turn finished job %s status %s", job.id, status)
        return self._success_payload(job.id, session.id, packet, prompt, text, status)

    def get_job(self, job_id: str) -> dict[str, Any]:
        job = self._require_job(job_id)
        packet = self._read_packet(job)
        status = _status_value(getattr(job, "status", ""))
        return {
            "job_id": job.id,
            "agent_id": DEVELOPER_AGENT_ID,
            "session_id": getattr(job, "session_id", None),
            "status": status,
            "template_id": TEMPLATE_ID,
            "ran": status not in {JobStatus.QUEUED.value, ""},
            "queued_only": status == JobStatus.QUEUED.value,
            "visible": True,
            "packet": packet,
            "persisted_tool": False,
            "packaging_applied": False,
            "tool_checks": tool_checks_for_job(self._store, job.id),
            "watch": _watch(job.id, getattr(job, "session_id", None)),
        }

    def _success_payload(
        self,
        job_id: str,
        session_id: str,
        packet: Mapping[str, Any],
        prompt: str,
        reply: str,
        status: str,
    ) -> dict[str, Any]:
        return {
            "job_id": job_id,
            "agent_id": DEVELOPER_AGENT_ID,
            "session_id": session_id,
            "status": status,
            "template_id": TEMPLATE_ID,
            "ran": True,
            "queued_only": False,
            "mediation": "developer_turn",
            "visible": True,
            "prompt": prompt,
            "reply": reply,
            "packet": dict(packet),
            "persisted_tool": False,
            "packaging_applied": False,
            "tool_checks": tool_checks_for_job(self._store, job_id),
            "watch": _watch(job_id, session_id),
        }

    def _require_store(self) -> None:
        if self._store is None or not hasattr(self._store, "create_session"):
            raise ToolsAuthoringError("Developer mediation is unavailable.", 503, ran=False)

    def _require_orchestrator(self) -> None:
        if self._orchestrator is None or not hasattr(self._orchestrator, "create_job_with_phases"):
            raise ToolsAuthoringError("Developer mediation is unavailable.", 503, ran=False)
        if not hasattr(self._orchestrator, "start_phase"):
            raise ToolsAuthoringError("Developer mediation is unavailable.", 503, ran=False)

    def _require_kernel(self) -> Any:
        run_turn = getattr(self._kernel, "run_turn", None)
        if not callable(run_turn):
            raise ToolsAuthoringError("Developer mediation is unavailable.", 503, ran=False)
        return self._kernel

    def _require_developer(self) -> Any:
        getter = getattr(self._registry, "get_profile", None)
        if not callable(getter):
            raise ToolsAuthoringError("Developer agent is unavailable.", 503, ran=False)
        profile = getter(DEVELOPER_AGENT_ID)
        if profile is None:
            raise ToolsAuthoringError("Developer agent is unavailable.", 503, ran=False)
        return profile

    def _create_job(self, packet: Mapping[str, Any], session_id: str) -> Any:
        draft = packet["draft"]
        name = draft.get("tool_name") or "new tool"
        return self._orchestrator.create_job_with_phases(
            goal=f"Tools Studio {packet['intent']}: {name}",
            session_id=session_id,
            agent_id=DEVELOPER_AGENT_ID,
            phase_specs=[
                PhaseSpec(
                    name="Author",
                    success_rule=SUCCESS_RULE,
                    assigned_agent_id=DEVELOPER_AGENT_ID,
                    # The phase rule is about Developer's reply. The tool itself is checked
                    # at registration (tool_check.py), with or without a job [CARD-511 D1].
                    verify_checker=None,
                    max_turns=8,
                )
            ],
            template_id=TEMPLATE_ID,
            success_rule=SUCCESS_RULE,
        )

    def _seed_intake(self, job: Any) -> None:
        phase = self._author_phase(job.id)
        matched = getattr(self._orchestrator, "_matched_ids", None)
        if isinstance(matched, dict):
            matched[job.id] = [MATCHED_CAPABILITY_ID]
        saver = getattr(self._store, "save_job_phase_checkpoint", None)
        if callable(saver):
            saver(
                job_id=job.id,
                phase_id=phase.id,
                phase_index=int(getattr(phase, "index", 0) or 0),
                verifier_status="none",
                matched_capability_ids=[MATCHED_CAPABILITY_ID],
            )

    def _stamp_packet(self, job: Any, packet: Mapping[str, Any]) -> None:
        phase = self._author_phase(job.id)
        phase.input_packet_json = _handoff_json(
            f"Tools Studio {packet['intent']}: {packet['draft'].get('tool_name') or 'new tool'}",
            _prefixed_json(packet),
        )
        phase.assigned_agent_id = DEVELOPER_AGENT_ID
        self._store.update_phase(phase)
        self._record_event(
            job.id,
            PACKET_EVENT_KIND,
            {
                "schema": PACKET_SCHEMA,
                "version": PACKET_VERSION,
                "studio": "tools",
                "intent": packet["intent"],
                "tool_name": packet["draft"].get("tool_name") or "",
                "agent_id": DEVELOPER_AGENT_ID,
                "session_id": getattr(job, "session_id", None),
                "packet": packet,
            },
        )

    def _finish_phase(self, job_id: str, phase_id: str, session_id: str, text: str) -> str:
        phase = self._store.get_phase(phase_id)
        status = _status_value(getattr(phase, "status", ""))
        if status == PhaseStatus.RUNNING.value:
            if self._pending_approvals(session_id):
                self._orchestrator.park_phase(phase_id)
            else:
                fresh = self._store.get_phase(phase_id)
                self._orchestrator.complete_phase(phase_id, output_packet_for_phase(fresh, text))
        job = self._store.get_job(job_id)
        return _status_value(getattr(job, "status", ""))

    def _pending_approvals(self, session_id: str) -> bool:
        getter = getattr(self._store, "get_pending_approvals", None)
        if not callable(getter):
            return False
        try:
            pending = getter(session_id=session_id) or []
        except TypeError:
            return False
        except Exception:
            return False
        return bool(pending)

    def _ensure_assistant_message(self, session_id: str, text: str) -> None:
        messages = list(self._store.get_messages(session_id) or [])
        for message in messages:
            if _role_value(message) == Role.ASSISTANT.value and str(getattr(message, "content", "") or "").strip():
                return
        self._store.save_message(
            session_id=session_id,
            agent_id=DEVELOPER_AGENT_ID,
            message=ChatMessage(role=Role.ASSISTANT, content=text),
        )

    def _close_failed(self, job_id: str, phase_id: str, reason: str) -> str:
        try:
            phase = self._store.get_phase(phase_id)
            status = _status_value(getattr(phase, "status", ""))
            if status == PhaseStatus.RUNNING.value:
                self._orchestrator.fail_phase(phase_id, reason)
                return JobStatus.FAILED.value
            if status in {PhaseStatus.QUEUED.value, PhaseStatus.WAITING_APPROVAL.value}:
                self._orchestrator.cancel_job(job_id)
                return JobStatus.CANCELLED.value
        except Exception:
            logger.exception("Could not close tools mediation job %s", job_id)
        return JobStatus.FAILED.value

    def _author_phase(self, job_id: str) -> Any:
        phases = list(self._store.list_phases_for_job(job_id) or [])
        if not phases:
            raise ToolsAuthoringError(f"Job {job_id} has no author phase.", 404, ran=False)
        return phases[0]

    def _require_job(self, job_id: str) -> Any:
        getter = getattr(self._store, "get_job", None)
        if not callable(getter):
            raise ToolsAuthoringError("job store is unavailable", 503, ran=False)
        try:
            job = getter(str(job_id or "").strip())
        except Exception as exc:
            raise ToolsAuthoringError(f"Job {job_id} not found.", 404, ran=False) from exc
        if job is None or getattr(job, "template_id", None) != TEMPLATE_ID:
            raise ToolsAuthoringError(f"Job {job_id} not found.", 404, ran=False)
        if getattr(job, "agent_id", None) != DEVELOPER_AGENT_ID:
            raise ToolsAuthoringError(f"Job {job_id} not found.", 404, ran=False)
        return job

    def _read_packet(self, job: Any) -> Optional[dict[str, Any]]:
        phase = self._author_phase(job.id)
        return _load_packet(getattr(phase, "input_packet_json", None))

    def _record_event(self, job_id: str, kind: str, payload: Mapping[str, Any]) -> None:
        saver = getattr(self._store, "save_standing_journey_event", None)
        if callable(saver):
            saver(job_id=job_id, kind=kind, payload=dict(payload))


def _watch(job_id: str, session_id: Optional[str]) -> dict[str, Any]:
    return {
        "primary": "chat",
        "chat": {
            "studio": "chat",
            "job_id": job_id,
            "session_id": session_id,
            "agent_id": DEVELOPER_AGENT_ID,
        },
        "observe": {
            "studio": "observe",
            "tab": "observability",
            "job_id": job_id,
        },
    }
