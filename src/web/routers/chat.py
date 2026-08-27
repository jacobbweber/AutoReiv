"""
Chat & Session Management Router [REQ-WEB-001, REQ-VERIFY-006, REQ-PLAN-006].
"""

import json
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.domain.kernel.models import KernelEventType


class CreateSessionRequest(BaseModel):
    agent_id: str
    title: str = "New Chat"


class ChatStreamRequest(BaseModel):
    agent_id: str
    session_id: str
    content: str


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
    profile = registry.get_profile(req.agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
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
