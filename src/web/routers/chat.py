import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEventType
from src.domain.planning.models import StepStatus

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


class CreateSessionRequest(BaseModel):
    agent_id: str
    title: str = "New Chat"


class ChatStreamRequest(BaseModel):
    agent_id: str
    session_id: str
    content: str
    goal_mode: bool = False
    self_verify: bool = False


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
async def list_sessions(request: Request, agent_id: Optional[str] = None):
    store = request.app.state.store
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
    store = request.app.state.store

    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

    async def worker():
        """Shielded execution worker decoupled from client SSE connection [REQ-MOB-STREAM-001]."""
        try:
            if req.goal_mode and plan_engine:
                # Save user prompt once to session history
                user_msg = ChatMessage(role=Role.USER, content=req.content)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=user_msg)

                plan = await plan_engine.formulate_plan(agent=profile, goal=req.content, session_id=req.session_id)
                plan_data = json.dumps(
                    {
                        "plan_id": plan.id,
                        "goal": plan.goal,
                        "steps": [{"title": s.title, "description": s.description} for s in plan.steps],
                    }
                )
                await queue.put(f"event: plan_formulated\ndata: {plan_data}\n\n")

                accumulated_context: List[str] = []
                for i, step in enumerate(plan.steps):
                    step.status = StepStatus.IN_PROGRESS
                    await queue.put(
                        f"event: step_start\ndata: {json.dumps({'step_index': i, 'title': step.title, 'description': step.description})}\n\n"
                    )

                    step_prompt = (
                        f"You are executing Step {i + 1}/{len(plan.steps)} of the goal: '{plan.goal}'.\n"
                        f"STEP: {step.title} - {step.description}\n"
                        f"PRIOR CONTEXT:\n" + "\n".join(accumulated_context)
                    )

                    if req.self_verify and reflexion_engine:
                        async def _on_step_progress(kind, payload, _i=i):
                            data = dict(payload)
                            data["step_index"] = _i
                            event = "reflexion_attempt" if kind == "attempt" else "reflexion_critique"
                            await queue.put(f"event: {event}\ndata: {json.dumps(data)}\n\n")

                        turn_res = await reflexion_engine.run_reflexion_turn(
                            agent=profile,
                            session_id=req.session_id,
                            user_content=step_prompt,
                            max_refinements=3,
                            save_to_history=False,
                            use_builtin_critic=True,
                            on_progress=_on_step_progress,
                        )
                        step_output = turn_res.get("output", "")
                        await queue.put(
                            f"event: reflexion_verified\ndata: {json.dumps({'step_index': i, 'passed': bool(turn_res.get('verification_passed')), 'status': turn_res.get('status')})}\n\n"
                        )
                    else:
                        reply = await kernel.run_turn(
                            agent=profile, session_id=req.session_id, user_content=step_prompt, save_to_history=False
                        )
                        step_output = reply.content

                    step.status = StepStatus.COMPLETED
                    step.result_summary = step_output
                    accumulated_context.append(f"Step {i + 1} ({step.title}): {step_output}")
                    await queue.put(
                        f"event: step_complete\ndata: {json.dumps({'step_index': i, 'status': 'completed'})}\n\n"
                    )

                synth_prompt = (
                    f"Synthesize the final deliverable for the goal: '{plan.goal}' based on completed steps:\n"
                    + "\n".join(accumulated_context)
                    + "\n\nCRITICAL FORMATTING INSTRUCTIONS:\n"
                    "- Format the entire deliverable in clean, rich GitHub-flavored Markdown.\n"
                    "- Use clear markdown headings (##, ###), bulleted action items, checklists, and summary tables.\n"
                    "- Do NOT output raw JSON objects, JSON code blocks, or Python dictionaries.\n"
                    "- Present the finalized output directly as a polished, human-readable report."
                )
                final_reply = await kernel.run_turn(
                    agent=profile, session_id=req.session_id, user_content=synth_prompt, save_to_history=False
                )
                final_content = format_json_deliverable_to_markdown(final_reply.content)
                # Save final assistant reply to session history
                asst_msg = ChatMessage(role=Role.ASSISTANT, content=final_content)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=asst_msg)

                await queue.put(f"event: token\ndata: {json.dumps({'text': final_content})}\n\n")
                await queue.put(f"event: turn_done\ndata: {json.dumps({'content': final_content})}\n\n")

            elif req.self_verify and reflexion_engine:
                user_msg = ChatMessage(role=Role.USER, content=req.content)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=user_msg)

                async def _on_progress(kind, payload):
                    event = "reflexion_attempt" if kind == "attempt" else "reflexion_critique"
                    await queue.put(f"event: {event}\ndata: {json.dumps(payload)}\n\n")

                turn_res = await reflexion_engine.run_reflexion_turn(
                    agent=profile,
                    session_id=req.session_id,
                    user_content=req.content,
                    max_refinements=3,
                    save_to_history=False,
                    use_builtin_critic=True,
                    on_progress=_on_progress,
                )
                verified_output = format_json_deliverable_to_markdown(turn_res.get("output", ""))
                asst_msg = ChatMessage(role=Role.ASSISTANT, content=verified_output)
                store.save_message(session_id=req.session_id, agent_id=profile.id, message=asst_msg)
                await queue.put(
                    f"event: reflexion_verified\ndata: {json.dumps({'passed': bool(turn_res.get('verification_passed')), 'status': turn_res.get('status')})}\n\n"
                )
                await queue.put(f"event: token\ndata: {json.dumps({'text': verified_output})}\n\n")
                await queue.put(f"event: turn_done\ndata: {json.dumps({'content': verified_output})}\n\n")

            else:
                async for event in kernel.stream_turn(profile, req.session_id, req.content):
                    if event.event_type == KernelEventType.TOKEN:
                        if event.reasoning_content:
                            data = json.dumps({"text": event.reasoning_content})
                            await queue.put(f"event: reasoning\ndata: {data}\n\n")
                        if event.content:
                            data = json.dumps({"text": event.content})
                            await queue.put(f"event: token\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.TOOL_START:
                        call_info = event.tool_call or {}
                        data = json.dumps(
                            {
                                "tool_name": call_info.get("name", ""),
                                "arguments": call_info.get("arguments", {}),
                            }
                        )
                        await queue.put(f"event: tool_start\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.TOOL_END:
                        out_text = event.tool_result.output if event.tool_result else ""
                        data = json.dumps({"result": out_text})
                        await queue.put(f"event: tool_output\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.HANDOFF_START:
                        data = json.dumps({"type": "handoff_start", **(event.handoff or {})})
                        await queue.put(f"event: handoff_start\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.HANDOFF_COMPLETE:
                        data = json.dumps({"type": "handoff_complete", **(event.handoff or {})})
                        await queue.put(f"event: handoff_complete\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.APPROVAL_REQUIRED:
                        data = json.dumps(
                            {
                                "approval_id": event.approval_id,
                                "tool_name": (event.tool_call or {}).get("name", ""),
                                "arguments": (event.tool_call or {}).get("arguments", {}),
                                "message": event.content,
                            }
                        )
                        await queue.put(f"event: approval_required\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.TURN_END:
                        data = json.dumps({"content": event.content})
                        await queue.put(f"event: turn_done\ndata: {data}\n\n")
                    elif event.event_type == KernelEventType.ERROR:
                        data = json.dumps({"error": event.content})
                        await queue.put(f"event: error\ndata: {data}\n\n")

        except Exception as e:
            logger.exception("Error in background chat stream worker: %s", e)
            err_data = json.dumps({"error": str(e)})
            await queue.put(f"event: error\ndata: {err_data}\n\n")
        finally:
            await queue.put(None)

    # Launch background worker detached from the HTTP generator lifecycle
    asyncio.create_task(worker())

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            # Client disconnected from SSE stream; worker task continues running in background
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
    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    plan = await plan_engine.formulate_plan(
        agent=profile,
        goal=req.goal,
        session_id=req.session_id,
    )

    completed_plan, final_output = await plan_engine.execute_plan(
        plan=plan,
        agent=profile,
    )

    return {
        "status": "completed" if completed_plan.is_completed else "failed",
        "goal": req.goal,
        "plan": completed_plan.model_dump(),
        "output": final_output,
    }
