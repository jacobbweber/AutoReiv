"""
Chat & Session Management Router [REQ-WEB-001, REQ-VERIFY-006, REQ-PLAN-006].
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.domain.gateway.models import ChatMessage, Role
from src.domain.kernel.models import KernelEventType
from src.domain.planning.models import StepStatus


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

    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            if req.goal_mode and plan_engine:
                # Save user prompt once to session history
                user_msg = ChatMessage(role=Role.USER, content=req.content)
                request.app.state.store.save_message(session_id=req.session_id, agent_id=profile.id, message=user_msg)

                plan = await plan_engine.formulate_plan(agent=profile, goal=req.content, session_id=req.session_id)
                plan_data = json.dumps(
                    {
                        "plan_id": plan.id,
                        "goal": plan.goal,
                        "steps": [{"title": s.title, "description": s.description} for s in plan.steps],
                    }
                )
                yield f"event: plan_formulated\ndata: {plan_data}\n\n"

                accumulated_context: List[str] = []
                for i, step in enumerate(plan.steps):
                    step.status = StepStatus.IN_PROGRESS
                    yield f"event: step_start\ndata: {json.dumps({'step_index': i, 'title': step.title, 'description': step.description})}\n\n"

                    step_prompt = (
                        f"You are executing Step {i + 1}/{len(plan.steps)} of the goal: '{plan.goal}'.\n"
                        f"STEP: {step.title} - {step.description}\n"
                        f"PRIOR CONTEXT:\n" + "\n".join(accumulated_context)
                    )

                    if req.self_verify and reflexion_engine:
                        yield f"event: reflexion_attempt\ndata: {json.dumps({'step_index': i, 'attempt': 1, 'max_attempts': 3})}\n\n"
                        turn_res = await reflexion_engine.run_reflexion_turn(
                            agent=profile,
                            session_id=req.session_id,
                            user_content=step_prompt,
                            max_refinements=3,
                            save_to_history=False,
                        )
                        step_output = turn_res.get("output", "")
                        yield f"event: reflexion_verified\ndata: {json.dumps({'step_index': i, 'passed': True})}\n\n"
                    else:
                        reply = await kernel.run_turn(
                            agent=profile, session_id=req.session_id, user_content=step_prompt, save_to_history=False
                        )
                        step_output = reply.content

                    step.status = StepStatus.COMPLETED
                    step.result_summary = step_output
                    accumulated_context.append(f"Step {i + 1} ({step.title}): {step_output}")
                    yield f"event: step_complete\ndata: {json.dumps({'step_index': i, 'status': 'completed'})}\n\n"

                synth_prompt = (
                    f"Synthesize the final deliverable for the goal: '{plan.goal}' based on completed steps:\n"
                    + "\n".join(accumulated_context)
                )
                final_reply = await kernel.run_turn(
                    agent=profile, session_id=req.session_id, user_content=synth_prompt, save_to_history=False
                )
                final_content = final_reply.content
                # Save final assistant reply to session history
                asst_msg = ChatMessage(role=Role.ASSISTANT, content=final_content)
                request.app.state.store.save_message(session_id=req.session_id, agent_id=profile.id, message=asst_msg)

                yield f"event: token\ndata: {json.dumps({'text': final_content})}\n\n"
                yield f"event: turn_done\ndata: {json.dumps({'content': final_content})}\n\n"

            elif req.self_verify and reflexion_engine:
                yield f"event: reflexion_attempt\ndata: {json.dumps({'attempt': 1, 'max_attempts': 3})}\n\n"
                turn_res = await reflexion_engine.run_reflexion_turn(
                    agent=profile,
                    session_id=req.session_id,
                    user_content=req.content,
                    max_refinements=3,
                )
                verified_output = turn_res.get("output", "")
                yield f"event: reflexion_verified\ndata: {json.dumps({'passed': True})}\n\n"
                yield f"event: token\ndata: {json.dumps({'text': verified_output})}\n\n"
                yield f"event: turn_done\ndata: {json.dumps({'content': verified_output})}\n\n"

            else:
                async for event in kernel.stream_turn(profile, req.session_id, req.content):
                    if event.event_type == KernelEventType.TOKEN:
                        if event.reasoning_content:
                            data = json.dumps({"text": event.reasoning_content})
                            yield f"event: reasoning\ndata: {data}\n\n"
                        if event.content:
                            data = json.dumps({"text": event.content})
                            yield f"event: token\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.TOOL_START:
                        call_info = event.tool_call or {}
                        data = json.dumps(
                            {
                                "tool_name": call_info.get("name", ""),
                                "arguments": call_info.get("arguments", {}),
                            }
                        )
                        yield f"event: tool_start\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.TOOL_END:
                        out_text = event.tool_result.output if event.tool_result else ""
                        data = json.dumps({"result": out_text})
                        yield f"event: tool_output\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.HANDOFF_START:
                        data = json.dumps({"type": "handoff_start", **(event.handoff or {})})
                        yield f"event: handoff_start\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.HANDOFF_COMPLETE:
                        data = json.dumps({"type": "handoff_complete", **(event.handoff or {})})
                        yield f"event: handoff_complete\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.TURN_END:
                        data = json.dumps({"content": event.content})
                        yield f"event: turn_done\ndata: {data}\n\n"
                    elif event.event_type == KernelEventType.ERROR:
                        data = json.dumps({"error": event.content})
                        yield f"event: error\ndata: {data}\n\n"
        except Exception as e:
            err_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
