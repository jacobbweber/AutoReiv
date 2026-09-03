import asyncio
import json
import logging
import mimetypes
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.application.orchestration.chat_job_binding import (
    latest_open_job_for_session,
    output_packet_for_phase,
    persist_plan_as_job,
    phase_assignment_prompt,
    verify_skip_fact,
)
from src.application.orchestration.workflow_service import instantiate_workflow
from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEventType
from src.domain.orchestration.models import PhaseStatus
from src.domain.planning.models import ExecutionPlan, PlanStep, StepStatus
from src.infrastructure.memory.repositories.workflows import WorkflowStore

GOAL_PLAN_REVIEW_TOOL = "goal_plan_review"

logger = logging.getLogger(__name__)

# Active background generation tasks by session_id [REQ-RESIL-003, CARD-114 Finding 4]
_active_stream_tasks: Dict[str, asyncio.Task] = {}


def format_prompt_with_attachments(
    content: Optional[str],
    attachments: Optional[List[Dict[str, Any]]],
) -> str:
    """Format user prompt together with uploaded media and file attachments [CARD-143]."""
    text = (content or "").strip()
    if not attachments:
        return text

    att_blocks = []
    for att in attachments:
        fname = att.get("filename", "attachment")
        url = att.get("url", "")
        ctype = att.get("content_type", "unknown")
        size = att.get("size_bytes", 0)
        local_path = att.get("path", "")

        is_image = ctype.startswith("image/") or fname.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
        )
        is_doc = fname.lower().endswith(
            (".pdf", ".xlsx", ".xlsm", ".xls", ".docx", ".doc", ".csv", ".tsv")
        )
        if is_image:
            att_blocks.append(
                f"![{fname}]({url})\n"
                f"*(Attached Image: `{fname}`, {size} bytes, format: `{ctype}`, Local Path: `{local_path}`)*"
            )
        elif is_doc:
            block = (
                f"📎 [{fname} ({size} bytes)]({url})\n"
                f"*(Attached Document: `{fname}`, {size} bytes, Local Path: `{local_path}`)*"
            )
            if local_path and Path(local_path).exists() and size < 16384:
                try:
                    from src.application.skills.document_extractors import extract_document
                    doc_res = extract_document(local_path, max_pages=5, max_rows=25)
                    if doc_res.get("success") and doc_res.get("content"):
                        block += f"\n\n**Document Content Preview:**\n{doc_res['content']}"
                except Exception:
                    pass
            att_blocks.append(block)
        else:
            block = f"📎 [{fname} ({size} bytes)]({url}) (Local Path: `{local_path}`)"
            if local_path and Path(local_path).exists() and size < 8192:
                try:
                    snippet = Path(local_path).read_text(encoding="utf-8", errors="replace")
                    block += f"\n```\n{snippet}\n```"
                except Exception:
                    pass
            att_blocks.append(block)

    attachment_section = (
        "\n\n---\n"
        + "\n\n".join(att_blocks)
        + "\n\n*(Note for Agent: The user has attached the files/images above. You can read documents using `read_document_file` or filesystem tools if needed.)*"
    )
    return f"{text}{attachment_section}".strip()


def format_json_deliverable_to_markdown(text: str) -> str:
    """
    [REQ-MOB-STREAM-004] Gracefully converts raw structured JSON deliverables into rich Markdown sections.
    """
    if not text or not isinstance(text, str):
        return text or ""
    clean = text.strip()
    if not clean.startswith("{") or not clean.endswith("}"):
        return text
    try:
        data = json.loads(clean)
        if not isinstance(data, dict):
            return text

        has_keys = any(
            k in data
            for k in ("goal", "action_plan", "wiki_inventory_summary", "steps", "summary", "status")
        )
        if not has_keys:
            return text

        sections: List[str] = []
        if "goal" in data:
            sections.append(f"## 🎯 Goal: {data['goal']}\n")
        if "status" in data:
            sections.append(f"**Status**: `{data['status']}`\n")

        if "wiki_inventory_summary" in data and isinstance(data["wiki_inventory_summary"], dict):
            sections.append("### 📊 Inventory Summary\n")
            for k, v in data["wiki_inventory_summary"].items():
                label = k.replace("_", " ").title()
                if isinstance(v, list):
                    sections.append(f"- **{label}**:")
                    for item in v:
                        sections.append(f"  - {item}")
                else:
                    sections.append(f"- **{label}**: `{v}`")
            sections.append("")

        if "action_plan" in data and isinstance(data["action_plan"], dict):
            ap = data["action_plan"]
            title = ap.get("title", "Action Plan")
            sections.append(f"### 📋 Action Plan: {title}\n")
            if isinstance(ap.get("steps"), list):
                for idx, s in enumerate(ap["steps"]):
                    num = s.get("step_number", idx + 1)
                    s_title = s.get("title", f"Step {num}")
                    sections.append(f"#### **Step {num}: {s_title}**")
                    if "objective" in s:
                        sections.append(f"- **Objective**: {s['objective']}")
                    if "actions" in s and isinstance(s["actions"], list):
                        sections.append("- **Actions**:")
                        for a in s["actions"]:
                            sections.append(f"  - {a}")
                    if "success_metric" in s:
                        sections.append(f"- **Success Metric**: {s['success_metric']}")
                    sections.append("")
        elif "steps" in data and isinstance(data["steps"], list):
            sections.append("### 📋 Execution Steps\n")
            for idx, s in enumerate(data["steps"]):
                num = s.get("step_number", idx + 1)
                s_title = s.get("title", f"Step {num}")
                sections.append(f"#### **Step {num}: {s_title}**")
                desc = s.get("description") or s.get("objective")
                if desc:
                    sections.append(f"- {desc}")
            sections.append("")

        handled = {"goal", "status", "wiki_inventory_summary", "action_plan", "steps"}
        for k, v in data.items():
            if k in handled:
                continue
            label = k.replace("_", " ").title()
            if isinstance(v, str):
                sections.append(f"### {label}\n\n{v}\n")
            elif isinstance(v, list):
                sections.append(f"### {label}\n")
                for item in v:
                    sections.append(f"- {json.dumps(item) if isinstance(item, dict) else item}")
                sections.append("")

        return "\n".join(sections).strip()
    except Exception:
        return text


def _sse(event: str, payload: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _plan_step_payload(plan: ExecutionPlan) -> list:
    return [{"title": s.title, "description": s.description} for s in plan.steps]


def last_goal_review_resume(store, session_id: str):
    """Return (status, approval record) when the last TOOL is a plan-review decide row."""
    try:
        msgs = store.get_messages(session_id=session_id)
    except Exception:
        return None
    last_tool = None
    for msg in reversed(list(msgs or [])):
        if getattr(msg, "role", None) == Role.TOOL:
            last_tool = msg
            break
    if not last_tool or getattr(last_tool, "name", None) != GOAL_PLAN_REVIEW_TOOL:
        return None
    tcid = getattr(last_tool, "tool_call_id", None) or ""
    if not str(tcid).startswith("resume_"):
        return None
    record = store.get_approval(str(tcid)[len("resume_") :])
    if not record:
        return None
    return str(record.get("status") or "").lower(), record


def execution_plan_from_approval(record: dict, session_id: str, agent_id: str):
    args = record.get("arguments") or {}
    raw_steps = args.get("steps") or []
    steps = []
    for i, raw in enumerate(raw_steps, 1):
        if not isinstance(raw, dict):
            continue
        steps.append(
            PlanStep(
                id=f"step_{i}",
                title=str(raw.get("title") or f"Step {i}"),
                description=str(raw.get("description") or ""),
            )
        )
    if not steps:
        return None
    plan = ExecutionPlan(
        id=str(args.get("plan_id") or "plan_review"),
        goal=str(args.get("goal") or ""),
        agent_id=agent_id,
        session_id=session_id,
        steps=steps,
    )
    self_verify = bool(args.get("self_verify"))
    approval_mode = str(args.get("approval_mode") or "ask")
    job_id = args.get("job_id")
    verify_checker = args.get("verify_checker")
    return plan, self_verify, approval_mode, job_id, verify_checker


async def _forward_kernel_event(queue, event, profile) -> None:
    if event.event_type == KernelEventType.TOKEN:
        if event.reasoning_content:
            await queue.put(_sse("reasoning", {"text": event.reasoning_content}))
        if event.content:
            await queue.put(_sse("token", {"text": event.content}))
    elif event.event_type == KernelEventType.TOOL_START:
        call_info = event.tool_call or {}
        await queue.put(
            _sse(
                "tool_start",
                {
                    "tool_name": call_info.get("name", ""),
                    "arguments": call_info.get("arguments", {}),
                },
            )
        )
    elif event.event_type == KernelEventType.TOOL_END:
        out_text = event.tool_result.output if event.tool_result else ""
        await queue.put(_sse("tool_output", {"result": out_text}))
    elif event.event_type == KernelEventType.HANDOFF_START:
        await queue.put(_sse("handoff_start", {"type": "handoff_start", **(event.handoff or {})}))
    elif event.event_type == KernelEventType.HANDOFF_COMPLETE:
        await queue.put(_sse("handoff_complete", {"type": "handoff_complete", **(event.handoff or {})}))
    elif event.event_type == KernelEventType.APPROVAL_REQUIRED:
        await queue.put(
            _sse(
                "approval_required",
                {
                    "approval_id": event.approval_id,
                    "tool_name": (event.tool_call or {}).get("name", ""),
                    "arguments": (event.tool_call or {}).get("arguments", {}),
                    "message": event.content,
                },
            )
        )
    elif event.event_type == KernelEventType.TURN_END:
        await queue.put(_sse("turn_done", {"content": event.content}))
    elif event.event_type == KernelEventType.REACT_STATE:
        payload = dict(event.react or {})
        if not payload.get("assigned_agent_id"):
            payload["assigned_agent_id"] = profile.id
        await queue.put(_sse("react_state", payload))
    elif event.event_type == KernelEventType.ERROR:
        await queue.put(_sse("error", {"error": event.content}))


async def _apply_verify_gate(
    *,
    queue,
    reflexion_engine,
    profile,
    phase,
    last_output: str,
    self_verify: bool,
    step_index: Optional[int] = None,
) -> Dict[str, Any]:
    """Named checker gate. Missing checker is an honest skip [REQ-ORCH-041]."""
    if not self_verify:
        return {"status": "not_requested", "verification_passed": False, "skipped": True, "facts": []}
    checker = (getattr(phase, "verify_checker", None) or "").strip()
    payload: Dict[str, Any] = {"phase_id": phase.id}
    if step_index is not None:
        payload["step_index"] = step_index
    if not checker or reflexion_engine is None:
        payload.update({"passed": False, "status": "skipped"})
        await queue.put(_sse("reflexion_verified", payload))
        return {
            "status": "skipped",
            "verification_passed": False,
            "skipped": True,
            "facts": [verify_skip_fact()],
        }
    result = await reflexion_engine.run_named_checker(
        agent=profile,
        last_output=last_output,
        verifier_tool_name=checker,
    )
    payload.update(
        {
            "passed": bool(result.get("verification_passed")),
            "status": result.get("status"),
            "discrepancies": result.get("discrepancies") or [],
        }
    )
    await queue.put(_sse("reflexion_verified", payload))
    return {
        "status": result.get("status"),
        "verification_passed": bool(result.get("verification_passed")),
        "skipped": False,
        "facts": [f"verify_checker: {checker}"],
        "discrepancies": result.get("discrepancies") or [],
    }


async def _stream_turn_bound(
    *,
    queue,
    kernel,
    orch,
    store,
    reflexion_engine,
    profile,
    session_id: str,
    user_content: Optional[str],
    approval_mode: str,
    resume: bool,
    job,
    phase,
    self_verify: bool,
    step_index: Optional[int] = None,
    emit_step_events: bool = False,
) -> str:
    """
    stream_turn one phase, then complete/fail/park.
    Returns done|parked|failed.
    """
    await queue.put(
        _sse(
            "phase_start",
            {
                "job_id": job.id,
                "phase_id": phase.id,
                "phase_name": phase.name,
                "index": phase.index,
                "assigned_agent_id": phase.assigned_agent_id or profile.id,
            },
        )
    )
    if emit_step_events:
        await queue.put(
            _sse(
                "step_start",
                {
                    "step_index": phase.index if step_index is None else step_index,
                    "title": phase.name,
                    "description": phase.success_rule,
                    "phase_id": phase.id,
                    "job_id": job.id,
                },
            )
        )

    outcome = "done"
    last_content = ""
    error_text = ""
    async for event in kernel.stream_turn(
        profile,
        session_id,
        user_content,
        approval_mode=approval_mode or "ask",
        resume=resume,
        job_id=job.id,
        phase_id=phase.id,
    ):
        await _forward_kernel_event(queue, event, profile)
        if event.event_type == KernelEventType.REACT_STATE:
            state = (event.react or {}).get("react_state")
            if state == "PARKED":
                outcome = "parked"
            elif state == "FAILED":
                outcome = "failed"
        elif event.event_type == KernelEventType.APPROVAL_REQUIRED:
            outcome = "parked"
        elif event.event_type == KernelEventType.ERROR:
            outcome = "failed"
            error_text = event.content or "stream error"
        elif event.event_type == KernelEventType.TURN_END:
            last_content = event.content or last_content

    if outcome == "parked":
        orch.park_phase(phase.id)
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "waiting_approval",
                    "react_state": "PARKED",
                },
            )
        )
        return "parked"
    if outcome == "failed":
        orch.fail_phase(phase.id, error_text or last_content or "phase failed")
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "failed",
                    "react_state": "FAILED",
                },
            )
        )
        return "failed"

    gate = await _apply_verify_gate(
        queue=queue,
        reflexion_engine=reflexion_engine,
        profile=profile,
        phase=phase,
        last_output=last_content,
        self_verify=self_verify,
        step_index=step_index,
    )
    if self_verify and not gate.get("skipped") and not gate.get("verification_passed"):
        detail = "; ".join(gate.get("discrepancies") or ["checker failed"])
        orch.fail_phase(phase.id, detail)
        await queue.put(
            _sse(
                "phase_complete",
                {
                    "job_id": job.id,
                    "phase_id": phase.id,
                    "status": "failed",
                    "react_state": "FAILED",
                },
            )
        )
        return "failed"

    orch.complete_phase(phase.id, output_packet_for_phase(phase, last_content, extra_facts=gate.get("facts") or []))
    await queue.put(
        _sse(
            "phase_complete",
            {
                "job_id": job.id,
                "phase_id": phase.id,
                "status": "done",
                "react_state": "DONE",
            },
        )
    )
    if emit_step_events:
        await queue.put(
            _sse(
                "step_complete",
                {
                    "step_index": phase.index if step_index is None else step_index,
                    "status": "completed",
                    "phase_id": phase.id,
                    "job_id": job.id,
                },
            )
        )
    return "done"


def _ensure_phase_session(store, session_id: str, phase, agent_id: str) -> str:
    phase_session = f"{session_id}::phase::{phase.id}"
    if store.get_session(phase_session) is None:
        store.create_session(agent_id=agent_id, title=phase.name or "Phase", session_id=phase_session)
    return phase_session


async def execute_goal_job_phases(
    *,
    queue,
    store,
    kernel,
    orch,
    reflexion_engine,
    profile,
    job,
    session_id: str,
    self_verify: bool,
    approval_mode: str,
) -> None:
    """Run each persisted phase via its own stream_turn after plan review [REQ-ORCH-039]."""
    phases = store.list_phases_for_job(job.id)
    accumulated: List[str] = []
    last_content = ""
    for phase in phases:
        current = store.get_phase(phase.id)
        if current.status in {PhaseStatus.DONE, PhaseStatus.FAILED, PhaseStatus.CANCELLED}:
            continue
        if current.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}:
            current = orch.start_phase(current.id)
        assignment = phase_assignment_prompt(job, current, len(phases), accumulated)
        phase_session = _ensure_phase_session(store, session_id, current, profile.id)
        outcome = await _stream_turn_bound(
            queue=queue,
            kernel=kernel,
            orch=orch,
            store=store,
            reflexion_engine=reflexion_engine,
            profile=profile,
            session_id=phase_session,
            user_content=assignment,
            approval_mode=approval_mode or "ask",
            resume=False,
            job=job,
            phase=current,
            self_verify=self_verify,
            step_index=current.index,
            emit_step_events=True,
        )
        if outcome != "done":
            return
        refreshed = store.get_phase(current.id)
        packet_text = refreshed.output_packet_json or ""
        accumulated.append(f"Phase {current.index + 1} ({current.name}): {packet_text[:1500]}")
        last_content = packet_text

    final_content = format_json_deliverable_to_markdown(last_content) if last_content else ""
    if final_content:
        store.save_message(
            session_id=session_id,
            agent_id=profile.id,
            message=ChatMessage(role=Role.ASSISTANT, content=final_content),
        )
        await queue.put(_sse("token", {"text": final_content}))
        await queue.put(_sse("turn_done", {"content": final_content}))
    elif not last_content:
        await queue.put(_sse("turn_done", {"content": ""}))


async def execute_goal_plan_steps(
    *,
    queue,
    store,
    kernel,
    reflexion_engine,
    profile,
    plan: ExecutionPlan,
    session_id: str,
    self_verify: bool,
    approval_mode: str,
    orch=None,
    job=None,
) -> None:
    """DTO adapter: persist if needed, then stream_turn each phase."""
    if orch is not None and job is None:
        job = persist_plan_as_job(orch, plan, verify_checker=None)
    if orch is not None and job is not None:
        await execute_goal_job_phases(
            queue=queue,
            store=store,
            kernel=kernel,
            orch=orch,
            reflexion_engine=reflexion_engine,
            profile=profile,
            job=job,
            session_id=session_id,
            self_verify=self_verify,
            approval_mode=approval_mode,
        )
        return
    # Last-resort DTO path without orchestrator (should not happen in app factory).
    accumulated_context: List[str] = []
    for i, step in enumerate(plan.steps):
        step.status = StepStatus.IN_PROGRESS
        await queue.put(
            _sse("step_start", {"step_index": i, "title": step.title, "description": step.description})
        )
        step_prompt = (
            f"You are executing Step {i + 1}/{len(plan.steps)} of the goal: '{plan.goal}'.\n"
            f"STEP: {step.title} - {step.description}\n"
            f"PRIOR CONTEXT:\n" + "\n".join(accumulated_context)
        )
        reply = await kernel.run_turn(
            agent=profile,
            session_id=session_id,
            user_content=step_prompt,
            save_to_history=False,
            approval_mode=approval_mode or "ask",
        )
        step.status = StepStatus.COMPLETED
        step.result_summary = reply.content
        accumulated_context.append(f"Step {i + 1} ({step.title}): {reply.content}")
        await queue.put(_sse("step_complete", {"step_index": i, "status": "completed"}))
    synth_prompt = (
        f"Synthesize the final deliverable for the goal: '{plan.goal}' based on completed steps:\n"
        + "\n".join(accumulated_context)
    )
    final_reply = await kernel.run_turn(
        agent=profile,
        session_id=session_id,
        user_content=synth_prompt,
        save_to_history=False,
        approval_mode=approval_mode or "ask",
    )
    final_content = format_json_deliverable_to_markdown(final_reply.content)
    store.save_message(session_id=session_id, agent_id=profile.id, message=ChatMessage(role=Role.ASSISTANT, content=final_content))
    await queue.put(_sse("token", {"text": final_content}))
    await queue.put(_sse("turn_done", {"content": final_content}))


class CreateSessionRequest(BaseModel):
    agent_id: str
    title: str = "New Chat"


class ChatStreamRequest(BaseModel):
    agent_id: str
    session_id: str
    content: Optional[str] = None
    resume: bool = False
    goal_mode: bool = False
    self_verify: bool = False
    approval_mode: str = "ask"
    verify_checker: Optional[str] = None
    workflow_id: Optional[str] = None
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


class GoalChatRequest(BaseModel):
    agent_id: str
    session_id: str
    goal: str


router = APIRouter(tags=["Chat"])


@router.get("/api/sessions")
async def list_sessions(
    request: Request,
    agent_id: Optional[str] = None,
    exclude_session_id: Optional[str] = None,
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
    return [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "title": s.title,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
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


@router.get("/api/sessions/{session_id}/messages")
async def get_session_messages(request: Request, session_id: str):
    store = request.app.state.store
    msgs = store.get_messages(session_id=session_id)
    return [
        {
            "role": m.role.value,
            "content": m.content,
            "name": m.name,
            "tool_calls": [tc.model_dump() for tc in m.tool_calls] if m.tool_calls else None,
            "tool_call_id": m.tool_call_id,
        }
        for m in msgs
    ]


@router.get("/api/chat/sessions/{session_id}/journey")
async def get_session_journey(request: Request, session_id: str):
    """Journey Timeline & Progress Inspector for active chat sessions [CARD-135]."""
    store = request.app.state.store
    sess = store.get_session(session_id)

    # 1. Retrieve Jobs & Phases for this session
    jobs_data = []
    if hasattr(store, "list_jobs_for_session"):
        raw_jobs = store.list_jobs_for_session(session_id)
        for j in raw_jobs:
            raw_phases = store.list_phases_for_job(j.id) if hasattr(store, "list_phases_for_job") else []
            phases_list = []
            for p in raw_phases:
                phases_list.append({
                    "id": p.id,
                    "index": p.index,
                    "name": p.name,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "assigned_agent_id": p.assigned_agent_id,
                    "success_rule": p.success_rule,
                    "verify_checker": getattr(p, "verify_checker", None),
                    "created_at": getattr(p, "created_at", None).isoformat() if hasattr(getattr(p, "created_at", None), "isoformat") else None,
                    "updated_at": getattr(p, "updated_at", None).isoformat() if hasattr(getattr(p, "updated_at", None), "isoformat") else None,
                })
            jobs_data.append({
                "id": j.id,
                "goal": j.goal,
                "status": j.status.value if hasattr(j.status, "value") else str(j.status),
                "created_at": j.created_at.isoformat() if hasattr(j.created_at, "isoformat") else str(j.created_at),
                "phases": phases_list,
            })

    # 2. Tool Executions (telemetry spans)
    tool_executions = []
    if hasattr(store, "get_telemetry_spans"):
        spans = store.get_telemetry_spans(session_id=session_id, limit=200)
        for s in spans:
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

    # 3. Session Artifacts
    artifacts_data = []
    if hasattr(store, "list_artifacts_for_session"):
        raw_artifacts = store.list_artifacts_for_session(session_id)
        for a in raw_artifacts:
            artifacts_data.append({
                "id": a.id,
                "title": a.title,
                "summary": a.summary,
                "content_type": a.content_type,
                "is_pinned": bool(a.is_pinned),
                "created_at": a.created_at.isoformat() if hasattr(a.created_at, "isoformat") else str(a.created_at),
            })

    # 4. Learned Facts
    facts_data = []
    if hasattr(store, "get_facts"):
        all_facts = store.get_facts()
        for f in all_facts:
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


@router.get("/api/chat/sessions/{session_id}/debug")
async def get_session_debug_payload(request: Request, session_id: str):
    """Per-Conversation Debug Inspector & Turn Payload Viewer [CARD-136]."""
    store = request.app.state.store
    registry = getattr(request.app.state, "registry", None)
    sess = store.get_session(session_id)

    # 1. Retrieve all stored messages
    msgs = store.get_messages(session_id=session_id)
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

    # 2. Retrieve telemetry spans for this session
    spans = []
    if hasattr(store, "get_telemetry_spans"):
        spans = store.get_telemetry_spans(session_id=session_id, limit=200)

    turn_spans = [s for s in spans if s.span_type == "turn"]
    tool_spans = [s for s in spans if s.span_type == "tool"]

    # 3. Aggregated metrics
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


@router.post("/api/chat/stream")
async def chat_stream(request: Request, req: ChatStreamRequest):
    registry = request.app.state.registry
    kernel = request.app.state.kernel
    plan_engine = getattr(request.app.state, "plan_engine", None)
    reflexion_engine = getattr(request.app.state, "reflexion_engine", None)
    orch = getattr(request.app.state, "job_orchestrator", None)
    store = request.app.state.store

    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
    verify_checker = (req.verify_checker or "").strip() or None
    self_verify = bool(req.self_verify)

    async def worker():
        """Shielded execution worker decoupled from client SSE connection [REQ-MOB-STREAM-001]."""
        try:
            resume = bool(req.resume)
            effective_content = format_prompt_with_attachments(req.content, req.attachments) if not resume else ""

            if (not resume) and req.goal_mode and plan_engine and not (req.workflow_id or "").strip():
                user_msg = ChatMessage(role=Role.USER, content=effective_content)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=user_msg)

                plan = await plan_engine.formulate_plan(
                    agent=profile, goal=effective_content, session_id=req.session_id
                )
                job = None
                if orch is not None:
                    job = persist_plan_as_job(
                        orch,
                        plan,
                        verify_checker=verify_checker if self_verify else None,
                    )
                    if job.current_phase_id:
                        orch.park_phase(job.current_phase_id)
                    await queue.put(
                        _sse(
                            "job_created",
                            {
                                "job_id": job.id,
                                "phase_count": len(store.list_phases_for_job(job.id)),
                                "goal": job.goal,
                                "agent_id": job.agent_id,
                                "session_id": job.session_id,
                                "status": "waiting_approval",
                            },
                        )
                    )
                approval_id = store.create_approval(
                    session_id=req.session_id,
                    agent_id=profile.id,
                    tool_name=GOAL_PLAN_REVIEW_TOOL,
                    arguments={
                        "plan_id": plan.id,
                        "goal": plan.goal,
                        "steps": _plan_step_payload(plan),
                        "self_verify": self_verify,
                        "approval_mode": req.approval_mode or "ask",
                        "job_id": job.id if job is not None else None,
                        "verify_checker": verify_checker if self_verify else None,
                    },
                )
                await queue.put(
                    _sse(
                        "plan_formulated",
                        {
                            "plan_id": plan.id,
                            "goal": plan.goal,
                            "steps": _plan_step_payload(plan),
                            "approval_id": approval_id,
                            "job_id": job.id if job is not None else None,
                        },
                    )
                )
                await queue.put(
                    _sse(
                        "approval_required",
                        {
                            "approval_id": approval_id,
                            "tool_name": GOAL_PLAN_REVIEW_TOOL,
                            "arguments": {"goal": plan.goal, "steps": _plan_step_payload(plan)},
                            "message": "Review the plan. Approve to run, or reject / send a message to revise.",
                        },
                    )
                )
                await queue.put(
                    _sse("turn_done", {"content": "Waiting for plan review.", "status": "plan_review_required"})
                )
                return

            workflow_id = (req.workflow_id or "").strip()
            if (not resume) and workflow_id and orch is not None:
                user_msg = ChatMessage(role=Role.USER, content=effective_content)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=user_msg)
                paths = getattr(request.app.state, "data_dir_paths", None)
                agents_path = getattr(paths, "agents_path", None) if paths is not None else None
                if agents_path is None:
                    await queue.put(_sse("error", {"error": "Data directory is not configured."}))
                    return
                try:
                    job = instantiate_workflow(
                        WorkflowStore(agents_path),
                        orch,
                        owner_agent_id=profile.id,
                        workflow_id=workflow_id,
                        goal=effective_content or "",
                        session_id=req.session_id,
                    )
                except KeyError as exc:
                    await queue.put(_sse("error", {"error": str(exc)}))
                    return
                await queue.put(
                    _sse(
                        "job_created",
                        {
                            "job_id": job.id,
                            "phase_count": len(store.list_phases_for_job(job.id)),
                            "goal": job.goal,
                            "agent_id": job.agent_id,
                            "session_id": job.session_id,
                            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                            "workflow_id": workflow_id,
                            "template_id": job.template_id,
                        },
                    )
                )
                await execute_goal_job_phases(
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
                )
                return

            if resume:
                review = last_goal_review_resume(store, req.session_id)
                if review:
                    status, record = review
                    if status in {"rejected", "reject"}:
                        args = record.get("arguments") or {}
                        if orch is not None and args.get("job_id"):
                            try:
                                orch.cancel_job(str(args["job_id"]))
                            except Exception:
                                logger.exception("Failed to cancel rejected goal job")
                        msg = "Plan rejected. Steps were not executed. Send a message to revise."
                        store.save_message(
                            session_id=req.session_id,
                            agent_id=profile.id,
                            message=ChatMessage(role=Role.ASSISTANT, content=msg),
                        )
                        await queue.put(_sse("token", {"text": msg}))
                        await queue.put(_sse("turn_done", {"content": msg}))
                        return
                    if status in {"approved", "approve"}:
                        rebuilt = execution_plan_from_approval(record, req.session_id, profile.id)
                        if rebuilt:
                            plan, stored_verify, stored_mode, job_id, stored_checker = rebuilt
                            job = None
                            if orch is not None and job_id:
                                try:
                                    job = store.get_job(str(job_id))
                                except Exception:
                                    job = None
                            if orch is not None and job is None:
                                job = persist_plan_as_job(
                                    orch,
                                    plan,
                                    verify_checker=stored_checker if stored_verify else None,
                                )
                            await execute_goal_plan_steps(
                                queue=queue,
                                store=store,
                                kernel=kernel,
                                reflexion_engine=reflexion_engine,
                                profile=profile,
                                plan=plan,
                                session_id=req.session_id,
                                self_verify=stored_verify,
                                approval_mode=stored_mode or req.approval_mode or "ask",
                                orch=orch,
                                job=job,
                            )
                            return

            job = None
            phase = None
            if orch is not None:
                if resume:
                    job = latest_open_job_for_session(store, req.session_id)
                    if job and job.current_phase_id:
                        phase = store.get_phase(job.current_phase_id)
                        if phase.status in {PhaseStatus.QUEUED, PhaseStatus.WAITING_APPROVAL}:
                            phase = orch.start_phase(phase.id)
                else:
                    job = orch.create_single_phase_job(
                        goal=effective_content or "Chat",
                        session_id=req.session_id,
                        agent_id=profile.id,
                        name="Chat",
                        success_rule=effective_content or "",
                        verify_checker=verify_checker if self_verify else None,
                    )
                    await queue.put(
                        _sse(
                            "job_created",
                            {
                                "job_id": job.id,
                                "phase_count": 1,
                                "goal": job.goal,
                                "agent_id": job.agent_id,
                                "session_id": job.session_id,
                                "status": "queued",
                            },
                        )
                    )
                    phase = orch.start_phase(job.current_phase_id)

            if orch is not None and job is not None and phase is not None:
                turn_content = None if resume else effective_content
                outcome = await _stream_turn_bound(
                    queue=queue,
                    kernel=kernel,
                    orch=orch,
                    store=store,
                    reflexion_engine=reflexion_engine,
                    profile=profile,
                    session_id=req.session_id,
                    user_content=turn_content,
                    approval_mode=req.approval_mode or "ask",
                    resume=resume,
                    job=job,
                    phase=phase,
                    self_verify=self_verify and not resume or (self_verify and bool(phase.verify_checker)),
                )
                if outcome == "done":
                    remaining = [
                        p
                        for p in store.list_phases_for_job(job.id)
                        if p.status == PhaseStatus.QUEUED
                    ]
                    prior = []
                    for nxt in remaining:
                        started = orch.start_phase(nxt.id)
                        assignment = phase_assignment_prompt(
                            job, started, len(store.list_phases_for_job(job.id)), prior
                        )
                        phase_session = _ensure_phase_session(store, req.session_id, started, profile.id)
                        nxt_outcome = await _stream_turn_bound(
                            queue=queue,
                            kernel=kernel,
                            orch=orch,
                            store=store,
                            reflexion_engine=reflexion_engine,
                            profile=profile,
                            session_id=phase_session,
                            user_content=assignment,
                            approval_mode=req.approval_mode or "ask",
                            resume=False,
                            job=job,
                            phase=started,
                            self_verify=self_verify,
                            step_index=started.index,
                            emit_step_events=True,
                        )
                        if nxt_outcome != "done":
                            break
                return

            turn_content = None if resume else req.content
            async for event in kernel.stream_turn(
                profile,
                req.session_id,
                turn_content,
                approval_mode=req.approval_mode or "ask",
                resume=resume,
            ):
                await _forward_kernel_event(queue, event, profile)

        except asyncio.CancelledError:
            logger.info("Chat stream worker cancelled for session: %s", req.session_id)
            await queue.put(_sse("turn_end", {"status": "aborted", "reason": "Stream aborted by user", "is_finished": True}))
            raise
        except Exception as e:
            logger.exception("Error in background chat stream worker: %s", e)
            await queue.put(_sse("error", {"error": str(e)}))
        finally:
            _active_stream_tasks.pop(req.session_id, None)
            await queue.put(None)

    # Cancel any previous task for this session if still running
    prev_task = _active_stream_tasks.get(req.session_id)
    if prev_task and not prev_task.done():
        prev_task.cancel()

    stream_task = asyncio.create_task(worker())
    _active_stream_tasks[req.session_id] = stream_task

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        except (asyncio.CancelledError, GeneratorExit):
            active_t = _active_stream_tasks.pop(req.session_id, None)
            if active_t and not active_t.done():
                active_t.cancel()
            raise
        finally:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/chat/stream/{session_id}/abort")
async def abort_stream_endpoint(request: Request, session_id: str):
    task = _active_stream_tasks.pop(session_id, None)
    was_cancelled = False
    if task and not task.done():
        task.cancel()
        was_cancelled = True

    # Mark any open jobs and phases in this session as cancelled
    store = getattr(request.app.state, "store", None)
    if store and hasattr(store, "list_jobs_for_session"):
        try:
            jobs = store.list_jobs_for_session(session_id)
            for j in jobs:
                if j.status not in ("done", "failed", "cancelled"):
                    store.update_job_status(j.id, "cancelled")
                    phases = store.list_phases_for_job(j.id)
                    for p in phases:
                        if p.status not in ("done", "failed", "cancelled"):
                            store.update_phase_status(p.id, "cancelled")
        except Exception as e:
            logger.warning("Failed to cancel active jobs/phases on abort: %s", e)

    telemetry = request.app.state.telemetry
    telemetry.record_turn_span(
        agent_id="system",
        session_id=session_id,
        model="streaming",
        success=False,
        error_message="Stream aborted by user",
    )
    return {"status": "aborted", "session_id": session_id, "task_cancelled": was_cancelled}


@router.post("/api/chat/verified")
async def chat_verified(request: Request, req: VerifiedChatRequest):
    registry = request.app.state.registry
    reflexion_engine = request.app.state.reflexion_engine
    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    res = await reflexion_engine.run_reflexion_turn(
        agent=profile,
        session_id=req.session_id,
        user_content=req.content,
        verifier_tool_name=req.verifier_tool,
        verifier_args=req.verifier_args,
        max_refinements=req.max_refinements,
    )
    return res


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


@router.post("/api/chat/goal")
async def chat_goal(request: Request, req: GoalChatRequest):
    registry = request.app.state.registry
    plan_engine = request.app.state.plan_engine
    orch = getattr(request.app.state, "job_orchestrator", None)
    store = request.app.state.store
    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    plan = await plan_engine.formulate_plan(
        agent=profile,
        goal=req.goal,
        session_id=req.session_id,
    )
    job = None
    if orch is not None:
        job = persist_plan_as_job(orch, plan)

    completed_plan, final_output = await plan_engine.execute_plan(
        plan=plan,
        agent=profile,
    )

    if orch is not None and job is not None:
        try:
            for phase in store.list_phases_for_job(job.id):
                current = store.get_phase(phase.id)
                if current.status == PhaseStatus.QUEUED:
                    current = orch.start_phase(current.id)
                if current.status == PhaseStatus.RUNNING:
                    orch.complete_phase(
                        current.id,
                        output_packet_for_phase(current, final_output),
                    )
        except Exception:
            logger.exception("Failed to close persisted job for /api/chat/goal")

    return {
        "status": "completed" if completed_plan.is_completed else "failed",
        "goal": req.goal,
        "plan": completed_plan.model_dump(),
        "output": final_output,
        "job_id": job.id if job is not None else None,
    }


def get_attachments_dir(request: Request) -> Path:
    """Resolve safe attachment storage directory [REQ-ATTACH-001]."""
    data_paths = getattr(request.app.state, "data_dir_paths", None)
    if data_paths and hasattr(data_paths, "root"):
        p = Path(data_paths.root) / "attachments"
    else:
        p = Path("data") / "attachments"
    p.mkdir(parents=True, exist_ok=True)
    return p


def sanitize_filename(filename: str) -> str:
    """Sanitize attachment filename to prevent directory traversal [REQ-ATTACH-001]."""
    basename = Path(filename).name
    clean = re.sub(r"[^\w\.-]", "_", basename)
    clean = clean.lstrip("._")
    return clean or "attachment.bin"


@router.post("/api/chat/upload")
async def chat_upload(
    request: Request,
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):
    """
    [REQ-ATTACH-001] Accept and safely persist media and document attachments.
    """
    raw_name = file.filename or "attachment.bin"
    safe_name = sanitize_filename(raw_name)
    file_id = uuid.uuid4().hex[:12]

    attachments_dir = get_attachments_dir(request)
    session_slug = sanitize_filename(session_id) if session_id else "global"
    target_dir = attachments_dir / session_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{file_id}_{safe_name}"
    contents = await file.read()
    target_path.write_bytes(contents)

    content_type = file.content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"

    return {
        "id": file_id,
        "filename": safe_name,
        "size_bytes": len(contents),
        "content_type": content_type,
        "url": f"/api/chat/attachments/{file_id}/{safe_name}",
        "path": str(target_path),
    }


@router.get("/api/chat/attachments/{file_id}/{filename}")
async def get_chat_attachment(
    request: Request,
    file_id: str,
    filename: str,
):
    """
    [REQ-ATTACH-002] Serve stored attachment files with proper Content-Type headers.
    """
    attachments_dir = get_attachments_dir(request)
    safe_file_id = re.sub(r"[^\w-]", "", file_id)
    safe_name = sanitize_filename(filename)

    matching_files = list(attachments_dir.glob(f"**/{safe_file_id}_{safe_name}"))
    if not matching_files or not matching_files[0].exists():
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = matching_files[0]
    content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    return FileResponse(path=file_path, media_type=content_type, filename=safe_name)
