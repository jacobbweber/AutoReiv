"""
FastAPI Chat Router [CARD-713].

Thin HTTP/SSE endpoint layer delegating phase-bound streaming, standing job
orchestration, active stream tracking, and attachment persistence to
``src/application/chat/``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.application.chat.attachments import (
    find_attachment_file,
    resolve_attachments_dir,
    sanitize_filename,
    save_uploaded_attachment,
)
from src.application.chat.job_resume import (
    GOAL_PLAN_REVIEW_TOOL,
    check_job_mint_preconditions,
    checkpoint_store_open_jobs,
    continue_remaining_resumed_phases,
    emit_and_execute_catalog_job,
    execution_plan_from_approval,
    last_goal_review_resume,
    resume_goal_review_if_any,
)
from src.application.chat.job_runner import (
    _ensure_phase_session,
    _plan_step_payload,
    execute_goal_job_phases,
    execute_goal_plan_steps,
    is_plan_awaiting_operator_choice,
    profile_for_phase,
    relay_phase_reply_to_parent,
    resume_session_for_phase,
)
from src.application.chat.stream_registry import (
    SSE_KEEPALIVE,
    SSE_KEEPALIVE_SECONDS,
    _active_stream_agents,
    _active_stream_tasks,
    _turn_side_tasks,
    cancel_turn_side_tasks,
    session_turn_running,
    spawn_turn_side_task,
    sse_with_keepalive,
)
from src.application.chat.stream_registry import (
    live_stream_session_ids as _live_stream_session_ids,
)
from src.application.chat.turn_streamer import (
    PHASE_COMPLETE_REFUSED_REASON,
    _apply_verify_gate,
    _background_extract_turn_memory,
    _forward_kernel_event,
    _phase_run_token,
    _plain_question_waits,
    _sse,
    _stream_turn_bound,
    complete_phase_or_fail,
    deduplicate_phase_deliverables,
    finalize_plain_turn_verification_and_memory,
    format_json_deliverable_to_markdown,
    format_prompt_with_attachments,
    maybe_update_first_turn_title,
    tool_output_payload,
)
from src.application.gateway.generation_semaphore import slot_wait_listener
from src.application.kernel.stopped_reply import PartialReply, stopped_message
from src.application.orchestration.chat_job_binding import (
    WAITING_FOR_ANSWER_NOTE,
    job_waiting_for_answer_on_session,
    latest_open_job_for_session,
)
from src.application.orchestration.repo_code_grounding import (
    apply_standing_repo_code_grounding,
    is_repo_code_ask,
)
from src.application.orchestration.session_activity import (
    build_session_debug_payload,
    build_session_journey,
    is_job_step_session,
    job_has_running_phase,
    session_activity,
)
from src.application.orchestration.working_set_context import (
    rebuild_working_set_after_resume,
)
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEventType
from src.domain.orchestration.models import PhaseStatus

__all__ = [
    "AuditAgentRequest", "ChatStreamRequest", "CreateSessionRequest", "GOAL_PLAN_REVIEW_TOOL",
    "PHASE_COMPLETE_REFUSED_REASON", "SSE_KEEPALIVE", "SSE_KEEPALIVE_SECONDS", "UpdateSessionRequest",
    "VerifiedChatRequest", "_active_stream_agents", "_active_stream_tasks", "_apply_verify_gate",
    "_background_extract_turn_memory", "_ensure_phase_session", "_forward_kernel_event", "_phase_run_token",
    "_plain_question_waits", "_plan_step_payload", "_sse", "_stream_turn_bound", "_turn_side_tasks",
    "apply_standing_repo_code_grounding", "cancel_turn_side_tasks", "chat_stream", "complete_phase_or_fail",
    "deduplicate_phase_deliverables", "execute_goal_job_phases", "execute_goal_plan_steps",
    "execution_plan_from_approval", "format_json_deliverable_to_markdown", "format_prompt_with_attachments",
    "get_attachments_dir", "is_plan_awaiting_operator_choice", "is_repo_code_ask", "last_goal_review_resume",
    "profile_for_phase", "rebuild_working_set_after_resume", "relay_phase_reply_to_parent",
    "resume_session_for_phase", "router", "sanitize_filename", "session_turn_running",
    "spawn_turn_side_task", "sse_with_keepalive", "tool_output_payload",
]

logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    agent_id: str
    title: str = "New Chat"


class UpdateSessionRequest(BaseModel):
    title: str


class ChatStreamRequest(BaseModel):
    agent_id: str
    session_id: str
    content: Optional[str] = None
    resume: bool = False
    # CARD-572: the Chat "Run as a job" box. Only this starts a standing Job; message text is never scanned.
    run_as_job: bool = False
    self_verify: bool = False
    approval_mode: str = "ask"
    verify_checker: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


class VerifiedChatRequest(BaseModel):
    agent_id: str
    session_id: str
    content: str
    verifier_tool: Optional[str] = None
    verifier_args: Optional[Dict[str, Any]] = None
    max_refinements: int = 3


class AuditAgentRequest(BaseModel):
    agent_id: str = "auditor-critic"
    session_id: str
    target_content: str


router = APIRouter(tags=["Chat"])


@router.get("/api/sessions")
async def list_sessions(
    request: Request,
    agent_id: Optional[str] = None,
    exclude_session_id: Optional[str] = None,
    include_steps: bool = False,
):
    store = request.app.state.store
    registry = getattr(request.app.state, "registry", None)
    if agent_id and registry:
        profile = registry.get_agent(agent_id)
        if profile:
            days = profile.history_retention_days if profile.history_retention_days is not None else 30
            store.prune_expired_sessions(
                agent_id=agent_id,
                max_age_days=days,
                exclude_session_id=exclude_session_id,
            )
    sessions = store.list_sessions(agent_id=agent_id)
    if not include_steps:  # CARD-608: job step sessions are not chats; their status rolls up to the parent
        sessions = [s for s in sessions if not is_job_step_session(s.id)]
    activity = session_activity(store, _live_stream_session_ids())  # CARD-493
    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
            "is_running": s.id in activity["running"],
            "waiting_approval": s.id in activity["waiting_approval"],
        }
        for s in sessions
    ]


@router.post("/api/sessions")
async def create_session(request: Request, req: CreateSessionRequest):
    store = request.app.state.store
    sess = store.create_session(agent_id=req.agent_id, title=req.title)
    return {
        "id": sess.id,
        "agent_id": sess.agent_id,
        "title": sess.title,
        "created_at": sess.created_at.isoformat(),
        "updated_at": sess.updated_at.isoformat(),
    }


@router.patch("/api/sessions/{session_id}")
async def update_session(request: Request, session_id: str, req: UpdateSessionRequest):
    store = request.app.state.store
    clean_title = req.title.strip()
    if not clean_title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    sess = store.update_session_title(session_id, clean_title)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {
        "id": sess.id,
        "agent_id": sess.agent_id,
        "title": sess.title,
        "created_at": sess.created_at.isoformat(),
        "updated_at": sess.updated_at.isoformat(),
    }


@router.delete("/api/sessions/{session_id}")
async def delete_session(request: Request, session_id: str):
    """Delete a chat session, its messages, and any step sessions [CARD-696]."""
    store = request.app.state.store
    task = _active_stream_tasks.pop(session_id, None)
    _active_stream_agents.pop(session_id, None)
    if task is not None and not task.done():
        task.cancel()
    cancel_turn_side_tasks(session_id, None)
    if not store.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"status": "deleted", "session_id": session_id}


@router.get("/api/sessions/{session_id}/messages")
async def get_session_messages(request: Request, session_id: str, include_archived: bool = False):
    from src.application.kernel.compaction_verifier import serialize_session_messages

    return serialize_session_messages(
        request.app.state.store,
        session_id,
        include_archived=include_archived,
    )


@router.get("/api/sessions/{session_id}/context")
async def get_session_context(request: Request, session_id: str):
    """Context window token consumption and authorized tools inspector (get_tools_for_agent) [CARD-161, CARD-699]."""
    from src.application.kernel.compaction_verifier import build_session_context_payload

    payload = build_session_context_payload(
        request.app.state.store,
        getattr(request.app.state, "registry", None),
        getattr(request.app.state, "tool_reg", None),
        session_id,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return payload


@router.post("/api/sessions/{session_id}/compact")
async def compact_session(request: Request, session_id: str):
    """Manually compact session conversation history early [CARD-161, CARD-699]."""
    from src.application.kernel.compaction_verifier import run_session_compaction

    payload = run_session_compaction(
        request.app.state.store,
        getattr(request.app.state, "registry", None),
        session_id,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return payload


@router.get("/api/chat/sessions/{session_id}/journey")
async def get_session_journey(request: Request, session_id: str):
    """Journey Timeline & Progress Inspector for active chat sessions [CARD-135, CARD-696]."""
    return build_session_journey(request.app.state.store, session_id)


@router.get("/api/chat/sessions/{session_id}/debug")
async def get_session_debug_payload(request: Request, session_id: str):
    """Per-Conversation Debug Inspector & Turn Payload Viewer [CARD-136, CARD-696]."""
    return build_session_debug_payload(
        request.app.state.store,
        getattr(request.app.state, "registry", None),
        session_id,
    )


@router.post("/api/chat/stream")
async def chat_stream(request: Request, req: ChatStreamRequest):
    registry = request.app.state.registry
    kernel = request.app.state.kernel
    reflexion_engine = getattr(request.app.state, "reflexion_engine", None)
    orch = getattr(request.app.state, "job_orchestrator", None)
    store = request.app.state.store

    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    if session_turn_running(req.session_id):
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "turn_running",
                "message": "A reply is still running in this chat. Wait for it to finish, or press Stop.",
            },
        )

    queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
    verify_checker = (req.verify_checker or "").strip() or None
    self_verify = bool(req.self_verify)

    async def worker():
        """Shielded execution worker decoupled from client SSE connection [REQ-MOB-STREAM-001]."""
        partial = PartialReply()  # CARD-489: words shown so far, kept if the reply is stopped
        slot_wait_listener.set(lambda kind, data: queue.put_nowait(_sse(kind, data)))
        try:
            resume = bool(req.resume)
            effective_content = ""
            if not resume:
                from src.application.gateway.attachment_text import attachment_char_budget, build_attachment_prompt
                from src.application.kernel.context_compactor import resolve_agent_context_limit

                built = build_attachment_prompt(
                    req.content,
                    req.attachments,
                    char_budget=attachment_char_budget(resolve_agent_context_limit(profile, store)) if req.attachments else 0,
                    direct=req.agent_id == "direct",
                    attachments_dir=(lambda: get_attachments_dir(request)) if req.attachments else None,
                )
                effective_content = built.text
                for failure in built.failures:  # REQ-479-003: the user is told too
                    await queue.put(_sse("attachment_notice", {"type": "attachment_notice", "message": failure}))
                maybe_update_first_turn_title(store, req.session_id, req.content)

            answer_job = None  # CARD-613: Jacob's message answers a job step's question and continues that step
            if not resume and not req.run_as_job and req.agent_id != "direct" and orch is not None and store:
                answer_job = job_waiting_for_answer_on_session(store, req.session_id)
                if answer_job is not None:
                    resume = True
                    store.save_message(
                        session_id=req.session_id,
                        agent_id=profile.id,
                        message=ChatMessage(role=Role.USER, content=effective_content),
                    )
            if resume:
                if answer_job is None and await resume_goal_review_if_any(
                    queue=queue,
                    store=store,
                    kernel=kernel,
                    orch=orch,
                    reflexion_engine=reflexion_engine,
                    profile=profile,
                    session_id=req.session_id,
                    approval_mode=req.approval_mode or "ask",
                ):
                    return

                # Resume an open multi-phase job (HITL park / mid-graph / crash) [CARD-219, CARD-253].
                if orch is not None:
                    job = latest_open_job_for_session(store, req.session_id)
                    if job and job.current_phase_id:
                        resume_info = None
                        resume_fn = getattr(orch, "resume_after_crash", None)
                        if callable(resume_fn):
                            resume_info = resume_fn(job.id)
                            if resume_info is not None and resume_info.needs_replan:
                                job = None
                            elif resume_info is not None and resume_info.resumed_from_checkpoint:
                                await queue.put(_sse("resumed_from_checkpoint", resume_info.as_dict()))
                                job = resume_info.job or job
                        if job and job.current_phase_id:
                            if (
                                resume_info is not None
                                and resume_info.resumed_from_checkpoint
                                and resume_info.continue_phase is not None
                            ):
                                phase = resume_info.continue_phase
                            else:
                                phase = store.get_phase(job.current_phase_id)
                            if phase.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}:
                                phase = orch.start_phase(phase.id)
                            resume_session = resume_session_for_phase(store, req.session_id, phase)
                            outcome = await _stream_turn_bound(
                                queue=queue,
                                kernel=kernel,
                                orch=orch,
                                store=store,
                                reflexion_engine=reflexion_engine,
                                profile=profile_for_phase(profile, phase, registry),
                                session_id=resume_session,
                                user_content=effective_content if answer_job is not None else None,
                                approval_mode=req.approval_mode or "ask",
                                resume=answer_job is None,
                                job=job,
                                phase=phase,
                                self_verify=bool(phase.verify_checker),
                            )
                            if outcome == "question":
                                relay_phase_reply_to_parent(store, req.session_id, resume_session, profile.id)
                                await queue.put(_sse("token", {"text": f"\n\n{WAITING_FOR_ANSWER_NOTE}\n"}))
                                await queue.put(_sse("turn_done", {"waiting_answer": True, "job_id": job.id}))
                            if outcome == "done":
                                # CARD-253: continue remaining phases (uses rebuild_working_set_after_resume).
                                await continue_remaining_resumed_phases(
                                    queue=queue,
                                    store=store,
                                    kernel=kernel,
                                    orch=orch,
                                    reflexion_engine=reflexion_engine,
                                    profile=profile,
                                    registry=registry,
                                    job=job,
                                    finished_phase=phase,
                                    resume_session=resume_session,
                                    parent_session_id=req.session_id,
                                    approval_mode=req.approval_mode or "ask",
                                    effective_content=effective_content,
                                    answer_job=answer_job,
                                )
                            return

            if req.agent_id == "direct":
                turn_content = None if resume else effective_content
                async for event in kernel.stream_turn(
                    profile,
                    req.session_id,
                    turn_content,
                    approval_mode=req.approval_mode or "ask",
                    resume=resume,
                ):
                    partial.observe(event)  # CARD-489: Direct replies keep their words on Stop too
                    if event.event_type == KernelEventType.TURN_END:
                        await queue.put(_sse("turn_done", {"content": event.content, "direct_mode": True}))
                    elif event.event_type != KernelEventType.REACT_STATE:
                        await _forward_kernel_event(queue, event, profile)
                return

            # CARD-572: a standing Job starts only when Jacob ticked Run as a job (no keyword routing).
            if (not resume) and req.run_as_job:
                # Fail-closed outcome mint [CARD-236 / REQ-JOBMINT-001]: cannot mint standing Job when orch missing.
                can_mint = await check_job_mint_preconditions(
                    queue=queue,
                    store=store,
                    orch=orch,
                    profile=profile,
                    session_id=req.session_id,
                    effective_content=effective_content,
                )
                if not can_mint:
                    return
                job = orch.create_job_from_catalog_resolve(
                    intent=effective_content,
                    session_id=req.session_id,
                    agent_id=profile.id,
                    role=profile.id,
                    verify_checker=verify_checker if self_verify else None,
                )
                # Emits job_created, catalog_resolved, and plan_formulated, then runs phases.
                await emit_and_execute_catalog_job(
                    queue=queue,
                    store=store,
                    kernel=kernel,
                    orch=orch,
                    reflexion_engine=reflexion_engine,
                    profile=profile,
                    job=job,
                    session_id=req.session_id,
                    self_verify=self_verify,
                    approval_mode=req.approval_mode or "ask",
                    capability_catalog=getattr(request.app.state, "capability_catalog", None),
                    wiki_root=getattr(request.app.state, "wiki_path", None),
                    registry=registry,
                )
                return

            # Short turns: plain AgentKernel ReAct (no Job/Phase formulation).
            turn_content = None if resume else effective_content
            last_plain = ""
            async for event in kernel.stream_turn(
                profile,
                req.session_id,
                turn_content,
                approval_mode=req.approval_mode or "ask",
                resume=resume,
                parts_request=None if resume else req.content,  # CARD-599: skipped-parts check on the typed text
            ):
                if event.event_type == KernelEventType.TURN_END and event.content:
                    last_plain = event.content
                partial.observe(event)
                await _forward_kernel_event(queue, event, profile)

            if not resume:
                llm_service = (
                    getattr(request.app.state, "gateway", None)
                    or getattr(kernel, "gateway", None)
                    or getattr(kernel, "llm_service", None)
                )
                data_dir = getattr(request.app.state, "data_dir", None) or getattr(kernel, "data_dir", None)
                await finalize_plain_turn_verification_and_memory(
                    queue=queue,
                    profile=profile,
                    session_id=req.session_id,
                    effective_content=effective_content,
                    last_plain=last_plain,
                    self_verify=self_verify,
                    verify_checker=verify_checker,
                    reflexion_engine=reflexion_engine,
                    llm_service=llm_service,
                    data_dir=data_dir,
                    spawn_side_task_fn=spawn_turn_side_task,
                    extract_memory_fn=_background_extract_turn_memory,
                )

        except asyncio.CancelledError:
            logger.info("Chat stream worker cancelled for session: %s", req.session_id)
            stopped = stopped_message(partial.text())  # CARD-489 [REQ-489-001/003]
            if stopped is not None and store and hasattr(store, "save_message"):
                try:
                    store.save_message(session_id=req.session_id, agent_id=profile.id, message=stopped)
                except Exception:
                    logger.exception("Failed to save the stopped reply")
            await queue.put(
                _sse(
                    "turn_end",
                    {
                        "status": "aborted",
                        "reason": "kill_checkpointed",
                        "is_finished": True,
                    },
                )
            )
            raise
        except Exception as e:
            logger.exception("Error in background chat stream worker: %s", e)
            err_msg = f"⚠️ **Error**: {e}"
            if store and hasattr(store, "save_message"):
                try:
                    store.save_message(
                        session_id=req.session_id,
                        agent_id=profile.id,
                        message=ChatMessage(role=Role.ASSISTANT, content=err_msg),
                    )
                except Exception:
                    logger.exception("Failed to persist error message to SQLite")
            await queue.put(_sse("error", {"error": str(e)}))
            await queue.put(_sse("turn_done", {"content": err_msg, "error": str(e)}))
        finally:
            if _active_stream_tasks.get(req.session_id) is asyncio.current_task():
                _active_stream_tasks.pop(req.session_id, None)
                _active_stream_agents.pop(req.session_id, None)
            await queue.put(None)

    stream_task = asyncio.create_task(worker())
    _active_stream_tasks[req.session_id] = stream_task
    _active_stream_agents[req.session_id] = profile.id

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for item in sse_with_keepalive(queue):
                yield item
        except (asyncio.CancelledError, GeneratorExit):
            logger.info("Client disconnected from SSE stream for session %s. Background worker shielded.", req.session_id)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


_job_has_running_phase = job_has_running_phase  # CARD-493: shared with Recent Chats


def _session_has_running_phase(store: Any, session_id: str) -> bool:
    if not store or not hasattr(store, "list_jobs_for_session"):
        return False
    try:
        for j in store.list_jobs_for_session(session_id) or []:
            status_val = j.status.value if hasattr(j.status, "value") else str(j.status)
            if status_val in ("in_progress", "running") and _job_has_running_phase(store, j):
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


@router.get("/api/sessions/activity")
async def get_sessions_activity(request: Request):
    """CARD-493: chat ids replying now and chat ids with a pending approval (Recent Chats markers)."""
    activity = session_activity(getattr(request.app.state, "store", None), _live_stream_session_ids())
    return {"running": sorted(activity["running"]), "waiting_approval": sorted(activity["waiting_approval"])}


@router.get("/api/sessions/{session_id}/status")
async def get_session_status(request: Request, session_id: str):
    """Check if server is actively generating or executing background work for session [CARD-154]."""
    task = _active_stream_tasks.get(session_id)
    is_running = bool(task and not task.done())
    active_agent = _active_stream_agents.get(session_id) if is_running else None

    store = getattr(request.app.state, "store", None)
    if not is_running and store and hasattr(store, "list_jobs_for_session"):
        try:
            jobs = store.list_jobs_for_session(session_id)
            for j in jobs:
                status_val = j.status.value if hasattr(j.status, "value") else str(j.status)
                if status_val in ("in_progress", "running") and _job_has_running_phase(store, j):
                    is_running = True
                    active_agent = j.agent_id
                    break
        except Exception:
            pass

    return {
        "session_id": session_id,
        "is_running": is_running,
        "active_agent": active_agent,
    }


@router.post("/api/chat/stream/{session_id}/abort")
async def abort_stream_endpoint(request: Request, session_id: str):
    """Operator kill mid-LLM: checkpoint + stop worker; same job_id stays resumable [CARD-259].

    Phase-level cancellation also invokes ``checkpoint_mid_llm_kill_phase`` inside ``_stream_turn_bound``.
    """
    task = _active_stream_tasks.pop(session_id, None)
    _active_stream_agents.pop(session_id, None)
    live = bool(task and not task.done())

    store = getattr(request.app.state, "store", None)
    orch = getattr(request.app.state, "job_orchestrator", None)
    checkpoint: dict = {
        "checkpointed": False,
        "resumable": True,
        "job_id": None,
        "phase_id": None,
        "reason": "operator_kill_mid_llm",
    }
    message = None
    ck_fn = getattr(orch, "checkpoint_mid_llm_kill", None) if orch is not None else None
    if not live:
        if _session_has_running_phase(store, session_id):
            checkpoint["reason"] = "not_started_by_chat"
            message = "This work was not started by a chat reply on this server, so Stop cannot end it. It was left running."
        else:
            checkpoint["reason"] = "nothing_running"
    elif callable(ck_fn):
        try:
            checkpoint = ck_fn(session_id) or checkpoint
        except Exception as e:
            logger.warning("Failed to checkpoint jobs on abort: %s", e)
    else:
        checkpoint = checkpoint_store_open_jobs(store, session_id, checkpoint)

    was_cancelled = False
    side_cancelled = cancel_turn_side_tasks(session_id, task) if task is not None else 0  # CARD-491
    if live:
        task.cancel()
        was_cancelled = True
        try:
            if task.get_loop() is asyncio.get_running_loop():
                await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError, RuntimeError, Exception):
            pass

    telemetry = request.app.state.telemetry
    telemetry.record_turn_span(
        agent_id="system",
        session_id=session_id,
        model="streaming",
        success=False,
        error_message="Stream aborted by user (kill_checkpointed)",
    )
    return {
        "status": "aborted",
        "session_id": session_id,
        "task_cancelled": was_cancelled,
        "checkpointed": bool(checkpoint.get("checkpointed")),
        "resumable": True,
        "job_id": checkpoint.get("job_id"),
        "phase_id": checkpoint.get("phase_id"),
        "reason": checkpoint.get("reason") or "operator_kill_mid_llm",
        "side_tasks_cancelled": side_cancelled,
        "message": message,
    }


@router.post("/api/chat/verified")
async def chat_verified(request: Request, req: VerifiedChatRequest):
    registry = request.app.state.registry
    reflexion_engine = request.app.state.reflexion_engine
    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    return await reflexion_engine.run_reflexion_turn(
        agent=profile,
        session_id=req.session_id,
        user_content=req.content,
        verifier_tool_name=req.verifier_tool,
        verifier_args=req.verifier_args,
        max_refinements=req.max_refinements,
    )


@router.post("/api/agents/audit")
async def audit_agent_action(request: Request, req: AuditAgentRequest):
    registry = request.app.state.registry
    kernel = request.app.state.kernel
    critic = registry.get_profile(req.agent_id or "auditor-critic")
    if not critic:
        raise HTTPException(status_code=404, detail=f"Auditor '{req.agent_id}' not found")

    audit_prompt = (
        "You are AutoReiv's Auditor Critic. Conduct a rigorous, adversarial review of the following proposed action or output:\n\n"
        f"{req.target_content}\n\n"
        "Provide: 1) Risk Score (1-10), 2) Challenged Assumptions, 3) Recommended Safety Guards."
    )

    reply = await kernel.run_turn(
        agent=critic,
        session_id=req.session_id,
        user_content=audit_prompt,
    )

    return {
        "status": "audited",
        "agent_id": critic.id,
        "session_id": req.session_id,
        "audit_report": reply.content,
    }


def get_attachments_dir(request: Request) -> Path:
    """Resolve safe attachment storage directory [REQ-ATTACH-001]."""
    return resolve_attachments_dir(getattr(request.app.state, "data_dir_paths", None))


@router.post("/api/chat/upload")
async def chat_upload(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):
    """[REQ-ATTACH-001] Accept and safely persist media and document attachments."""
    attachments_dir = get_attachments_dir(request)
    contents = await file.read()
    return save_uploaded_attachment(
        attachments_dir,
        raw_filename=file.filename,
        contents=contents,
        raw_content_type=file.content_type,
        session_id=session_id,
    )


@router.get("/api/chat/attachments/{file_id}/{filename}")
async def get_chat_attachment(
    request: Request,
    file_id: str,
    filename: str,
):
    """[REQ-ATTACH-002] Serve stored attachment files with proper Content-Type headers."""
    attachments_dir = get_attachments_dir(request)
    found = find_attachment_file(attachments_dir, file_id, filename)
    if found is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path, content_type, safe_name = found
    return FileResponse(path=file_path, media_type=content_type, filename=safe_name)
