import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
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
            if (not resume) and req.goal_mode and plan_engine:
                user_msg = ChatMessage(role=Role.USER, content=req.content)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=user_msg)

                plan = await plan_engine.formulate_plan(
                    agent=profile, goal=req.content, session_id=req.session_id
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
                user_msg = ChatMessage(role=Role.USER, content=req.content)
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
                        goal=req.content or "",
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
                        goal=req.content or "",
                        session_id=req.session_id,
                        agent_id=profile.id,
                        name="Chat",
                        success_rule=req.content or "",
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
                turn_content = None if resume else req.content
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

        except Exception as e:
            logger.exception("Error in background chat stream worker: %s", e)
            await queue.put(_sse("error", {"error": str(e)}))
        finally:
            await queue.put(None)

    asyncio.create_task(worker())

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
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
    telemetry = request.app.state.telemetry
    telemetry.record_turn_span(
        agent_id="system",
        session_id=session_id,
        model="streaming",
        success=False,
        error_message="Stream aborted by user",
    )
    return {"status": "aborted", "session_id": session_id}


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
