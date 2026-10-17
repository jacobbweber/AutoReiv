"""CARD-493: which chats are replying or waiting for approval, for Recent Chats.

The same rule as ``GET /api/sessions/{id}/status`` (CARD-486): a chat is replying while its stream worker runs,
or while one of its jobs has a RUNNING phase (a Stop leaves the job open with its phase QUEUED; that is not
running). A chat needs approval while a pending approval belongs to it or to one of its hand-off / phase sessions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Set

logger = logging.getLogger(__name__)

PHASE_SESSION_MARKER = "::phase::"
_CHILD_MARKERS = ("_child_", PHASE_SESSION_MARKER)
OPEN_JOB_STATUSES = ("running", "in_progress")


def parent_session_id(session_id: Any) -> str:
    """The chat a hand-off or phase session belongs to (``<sid>_child_...`` / ``<sid>::phase::...``)."""
    sid = str(session_id or "")
    for marker in _CHILD_MARKERS:
        if marker in sid:
            sid = sid.split(marker, 1)[0]
    return sid


def is_job_step_session(session_id: Any) -> bool:
    """CARD-608: ``<sid>::phase::<phase id>`` is a job step's own transcript, not a chat."""
    return PHASE_SESSION_MARKER in str(session_id or "")


def _status(value: Any) -> str:
    return str(getattr(value, "value", value) or "").lower()


def job_has_running_phase(store: Any, job: Any) -> bool:
    """True when a phase of ``job`` is RUNNING. Stores without phase listing keep the old job-level answer."""
    if not hasattr(store, "list_phases_for_job"):
        return True
    return any(_status(p.status) == "running" for p in store.list_phases_for_job(job.id) or [])


def session_activity(store: Any, live_session_ids: Iterable[str] = ()) -> Dict[str, Set[str]]:
    """``{"running": {...}, "waiting_approval": {...}}`` chat ids. Soft-fails to what it could read."""
    running: Set[str] = {parent_session_id(s) for s in live_session_ids if s}
    waiting: Set[str] = set()
    lister = getattr(store, "list_jobs_by_status", None)
    if callable(lister):
        for status in OPEN_JOB_STATUSES:
            try:
                for job in lister(status) or []:
                    sid = getattr(job, "session_id", None)
                    if sid and job_has_running_phase(store, job):
                        running.add(parent_session_id(sid))
            except Exception:  # noqa: BLE001
                logger.debug("session_activity: job scan failed", exc_info=True)
    pending = getattr(store, "get_pending_approvals", None)
    if callable(pending):
        try:
            for row in pending() or []:
                sid = row.get("session_id") if isinstance(row, dict) else None
                if sid:
                    waiting.add(parent_session_id(sid))
        except Exception:  # noqa: BLE001
            logger.debug("session_activity: approval scan failed", exc_info=True)
    return {"running": running, "waiting_approval": waiting}


def build_session_journey(store: Any, session_id: str) -> Dict[str, Any]:
    """Build the session journey payload for GET /api/chat/sessions/{session_id}/journey [CARD-135, CARD-696]."""
    from src.application.orchestration.kill_resume import (
        job_fail_reason,
        job_stopped_by_operator,
        job_waiting_for_answer,
        phase_fail_reason,
    )

    sess = store.get_session(session_id) if hasattr(store, "get_session") else None

    jobs_data = []
    if hasattr(store, "list_jobs_for_session"):
        raw_jobs = store.list_jobs_for_session(session_id)
        for j in raw_jobs:
            raw_phases = store.list_phases_for_job(j.id) if hasattr(store, "list_phases_for_job") else []
            phases_list = []
            for p in raw_phases:
                verify_status = None
                checker_name = getattr(p, "verify_checker", None)
                pkt = getattr(p, "output_packet_json", None) or ""
                p_status = p.status.value if hasattr(p.status, "value") else str(p.status)
                if "verify_status: verified" in pkt:
                    verify_status = "verified"
                elif "verify_status: failed" in pkt:
                    verify_status = "failed"
                elif "skipped_no_checker" in pkt or (not (checker_name or "").strip() and p_status == "done"):
                    verify_status = "skipped_no_checker"
                elif (checker_name or "").strip() and p_status == "failed":
                    verify_status = "failed"
                phases_list.append({
                    "id": p.id,
                    "index": p.index,
                    "name": p.name,
                    "status": p_status,
                    "assigned_agent_id": p.assigned_agent_id,
                    "success_rule": p.success_rule,
                    "verify_checker": checker_name,
                    "verify_status": verify_status,
                    "fail_reason": phase_fail_reason(p),
                    "created_at": getattr(p, "created_at", None).isoformat() if hasattr(getattr(p, "created_at", None), "isoformat") else None,
                    "updated_at": getattr(p, "updated_at", None).isoformat() if hasattr(getattr(p, "updated_at", None), "isoformat") else None,
                })
            phase_objs = list(raw_phases or [])
            jobs_data.append({
                "id": j.id,
                "goal": j.goal,
                "status": j.status.value if hasattr(j.status, "value") else str(j.status),
                "created_at": j.created_at.isoformat() if hasattr(j.created_at, "isoformat") else str(j.created_at),
                "phases": phases_list,
                "stopped": job_stopped_by_operator(store, j, phase_objs),
                "waiting_answer": job_waiting_for_answer(store, j, phase_objs),
                "fail_reason": job_fail_reason(store, j, phase_objs),
            })

    tool_executions = []
    if hasattr(store, "get_telemetry_spans"):
        for s in store.get_telemetry_spans(session_id=session_id, limit=200):
            if s.span_type == "tool":
                tool_executions.append({
                    "id": s.id,
                    "tool_name": s.name,
                    "duration_ms": round(s.duration_ms, 1),
                    "success": s.success,
                    "status": s.status,
                    "error_message": s.error_message,
                    "metadata": s.metadata or {},
                    "created_at": s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
                })

    artifacts_data = []
    if hasattr(store, "list_artifacts_for_session"):
        for a in store.list_artifacts_for_session(session_id):
            artifacts_data.append({
                "id": a.id,
                "title": a.title,
                "summary": a.summary,
                "content_type": a.content_type,
                "is_pinned": bool(a.is_pinned),
                "created_at": a.created_at.isoformat() if hasattr(a.created_at, "isoformat") else str(a.created_at),
            })

    facts_data = []
    if hasattr(store, "get_facts"):
        for f in store.get_facts():
            if f.get("source_session_id") == session_id:
                facts_data.append({
                    "entity": f.get("entity"),
                    "key": f.get("key"),
                    "value": f.get("value"),
                    "confidence": f.get("confidence", 1.0),
                })

    return {
        "session_id": session_id,
        "agent_id": sess.agent_id if sess else None,
        "title": sess.title if sess else "Chat Session",
        "jobs": jobs_data,
        "tool_executions": tool_executions,
        "artifacts": artifacts_data,
        "facts": facts_data,
        "summary": {
            "total_jobs": len(jobs_data),
            "total_tools_executed": len(tool_executions),
            "total_artifacts": len(artifacts_data),
            "total_facts_learned": len(facts_data),
        },
    }


def build_session_debug_payload(store: Any, registry: Any, session_id: str) -> Dict[str, Any]:
    """Build the session debug inspector payload for GET /api/chat/sessions/{session_id}/debug [CARD-136, CARD-696]."""
    sess = store.get_session(session_id) if hasattr(store, "get_session") else None

    msgs = store.get_messages(session_id=session_id) if hasattr(store, "get_messages") else []
    formatted_messages = [
        {
            "role": m.role.value,
            "content": m.content,
            "name": m.name,
            "tool_calls": [tc.model_dump() for tc in m.tool_calls] if m.tool_calls else None,
            "tool_call_id": m.tool_call_id,
        }
        for m in msgs
    ]

    spans = store.get_telemetry_spans(session_id=session_id, limit=200) if hasattr(store, "get_telemetry_spans") else []
    turn_spans = [s for s in spans if s.span_type == "turn"]
    tool_spans = [s for s in spans if s.span_type == "tool"]

    total_prompt_tokens = sum(s.prompt_tokens for s in turn_spans)
    total_completion_tokens = sum(s.completion_tokens for s in turn_spans)
    total_duration_ms = sum(s.duration_ms for s in spans)
    timed_turns = [s for s in turn_spans if s.ttft_ms is not None]
    avg_ttft_ms = sum(s.ttft_ms for s in timed_turns) / len(timed_turns) if timed_turns else 0.0

    latest_turn = turn_spans[0] if turn_spans else None
    active_model = latest_turn.model if latest_turn else "default"
    active_provider = latest_turn.provider if latest_turn else "ollama"

    system_prompt = ""
    if sess and registry:
        agent_profile = registry.get_profile(sess.agent_id)
        if agent_profile:
            system_prompt = agent_profile.system_prompt

    facts = []
    if hasattr(store, "get_facts"):
        all_facts = store.get_facts()
        facts = [f for f in all_facts if f.get("source_session_id") == session_id]

    return {
        "session_id": session_id,
        "agent_id": sess.agent_id if sess else None,
        "provider": active_provider,
        "model": active_model,
        "system_prompt": system_prompt,
        "message_count": len(formatted_messages),
        "raw_messages": formatted_messages,
        "turn_spans": [
            {
                "id": s.id,
                "name": s.name,
                "prompt_tokens": s.prompt_tokens,
                "completion_tokens": s.completion_tokens,
                "duration_ms": round(s.duration_ms, 1),
                "success": s.success,
                "metadata": s.metadata or {},
                "created_at": s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
            }
            for s in turn_spans
        ],
        "tool_payloads": [
            {
                "id": s.id,
                "name": s.name,
                "duration_ms": round(s.duration_ms, 1),
                "success": s.success,
                "metadata": s.metadata or {},
                "created_at": s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
            }
            for s in tool_spans
        ],
        "metrics": {
            "total_turns": len(turn_spans),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "total_duration_ms": round(total_duration_ms, 1),
            "avg_ttft_ms": round(avg_ttft_ms, 1),
        },
        "active_facts": facts,
    }

