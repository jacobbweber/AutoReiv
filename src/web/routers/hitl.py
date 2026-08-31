"""
Human-In-The-Loop (HITL) Action Approval Router [REQ-SAFE-005, REQ-SAFE-006, REQ-HITL-003].
"""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.orchestration.followup import PROPOSE_FOLLOWUP_TOOL, apply_followup_decision
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.skill_proposals import (
    SKILL_PROPOSAL_TOOLS,
    apply_skill_proposal_decision,
)
from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.hitl.models import ApprovalStatus

logger = logging.getLogger(__name__)


class DecisionRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    reason: Optional[str] = None
    session_id: Optional[str] = None


router = APIRouter(tags=["HITL"])


@router.get("/api/approvals/pending")
async def get_pending_approvals(request: Request, agent_id: Optional[str] = None, session_id: Optional[str] = None):
    store = request.app.state.store
    rows = store.get_pending_approvals(session_id=session_id, agent_id=agent_id)
    for row in rows:
        rid = str(row.get("routine_id") or "").strip()
        if rid and hasattr(store, "get_routine"):
            routine = store.get_routine(rid)
            row["routine_name"] = routine.name if routine else None
        else:
            row["routine_name"] = None
    return rows


@router.post("/api/approvals/{approval_id}/decision")
async def resolve_approval_endpoint(request: Request, approval_id: str, req: DecisionRequest):
    store = request.app.state.store
    record = store.get_approval(approval_id)
    resolved = store.resolve_approval(
        approval_id=approval_id,
        decision=req.decision,
        reason=req.reason,
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Approval not found or already resolved")

    execution = None
    decision_norm = (req.decision or "").strip().lower()
    if record and record.get("tool_name") == PROPOSE_FOLLOWUP_TOOL:
        args = record.get("arguments") or {}
        orch = JobPhaseOrchestrator(store)
        try:
            followup_result = apply_followup_decision(
                store,
                orch,
                proposal_id=args.get("proposal_id"),
                job_id=args.get("job_id"),
                decision=decision_norm,
                reason=req.reason,
            )
        except Exception:
            logger.exception("Follow-up proposal decision failed for %s", approval_id)
            followup_result = {"started": False, "error": "followup_decision_failed"}
        if decision_norm in {"approved", "approve"}:
            execution = {
                "ran": False,
                "tool_name": PROPOSE_FOLLOWUP_TOOL,
                "output": (
                    "Follow-up accepted. Job stays queued and was not auto-started. "
                    "A later user send/resume starts it; this path does not stream_turn."
                ),
                "followup": followup_result,
            }
        else:
            execution = {
                "ran": False,
                "tool_name": PROPOSE_FOLLOWUP_TOOL,
                "output": "Follow-up rejected. Job cancelled and will not run.",
                "followup": followup_result,
            }
    elif record and record.get("tool_name") in SKILL_PROPOSAL_TOOLS:
        args = record.get("arguments") or {}
        try:
            pack_result = apply_skill_proposal_decision(
                store,
                proposal_id=args.get("proposal_id"),
                decision=decision_norm,
                reason=req.reason,
            )
        except Exception:
            logger.exception("Skill/tool/workflow proposal decision failed for %s", approval_id)
            pack_result = {"disk_written": False, "error": "skill_proposal_decision_failed"}
        kind = str(args.get("kind") or record.get("tool_name") or "proposal")
        if decision_norm in {"approved", "approve"}:
            execution = {
                "ran": False,
                "tool_name": record.get("tool_name"),
                "output": (
                    f"{kind} accepted. Draft marked approved. "
                    "SKILL.md and src/ were not written. Agent Builder may call commit_skill_pack now."
                ),
                "skill_proposal": pack_result,
            }
        else:
            execution = {
                "ran": False,
                "tool_name": record.get("tool_name"),
                "output": f"{kind} rejected. Draft discarded. No files written.",
                "skill_proposal": pack_result,
            }
    elif decision_norm in {"approved", "approve"} and record:
        if record.get("tool_name") == "goal_plan_review":
            execution = {
                "ran": False,
                "tool_name": "goal_plan_review",
                "output": "Plan approved. Steps will run next.",
            }
        else:
            tool_reg = getattr(request.app.state, "tool_reg", None)
            registry = getattr(request.app.state, "registry", None)
            profile = registry.get_profile(record["agent_id"]) if registry else None
            if tool_reg and profile:
                tc = ToolCall(
                    id=f"resume_{approval_id}",
                    name=record["tool_name"],
                    arguments=record.get("arguments") or {},
                )
                tool_res = await tool_reg.execute(tc, profile, session_id=record.get("session_id"))
                execution = {
                    "ran": tool_res.success,
                    "tool_name": record["tool_name"],
                    "output": tool_res.output,
                    "error": tool_res.error,
                }
            else:
                execution = {
                    "ran": False,
                    "tool_name": record.get("tool_name"),
                    "error": "Registry or agent profile unavailable; approval recorded but tool was not executed.",
                }


    approval_session = str((record or {}).get("session_id") or "").strip()
    display_session = (req.session_id or "").strip() or approval_session
    if execution and execution.get("output") is not None:
        raw = execution["output"]
        content = raw if isinstance(raw, str) else json.dumps(raw, indent=2, default=str)
    elif execution and execution.get("error"):
        content = str(execution["error"])
    elif decision_norm in {"rejected", "reject"}:
        content = "Rejected. Tool did not run."
    else:
        content = "Approval recorded."

    tool_name = str((execution or {}).get("tool_name") or (record or {}).get("tool_name") or "tool")
    agent_id = str((record or {}).get("agent_id") or "assistant")
    tool_msg = ChatMessage(
        role=Role.TOOL,
        content=str(content),
        name=tool_name,
        tool_call_id=f"resume_{approval_id}",
    )
    routine_id = str((record or {}).get("routine_id") or "").strip()
    persist_sessions = []
    if approval_session:
        persist_sessions.append(approval_session)
    if display_session and display_session not in persist_sessions and not routine_id:
        persist_sessions.append(display_session)
    for sid in persist_sessions:
        try:
            store.save_message(session_id=sid, agent_id=agent_id, message=tool_msg)
        except Exception:
            logger.exception("Failed to persist HITL decision output for %s on %s", approval_id, sid)

    nested = None
    if approval_session and "_child_" in approval_session:
        registry = getattr(request.app.state, "registry", None)
        engine = getattr(registry, "handoff_engine", None) if registry else None
        kernel = getattr(request.app.state, "kernel", None)
        if engine is not None:
            if kernel is not None:
                engine.kernel = kernel
            parent_id = display_session if display_session and display_session != approval_session else None
            try:
                nested = await engine.resume_nested_child(
                    child_session_id=approval_session,
                    parent_session_id=parent_id,
                    approval_mode="ask",
                    agent_id=agent_id,
                )
            except Exception:
                logger.exception("Nested child HITL resume failed for %s", approval_id)

    routine_resume = None
    same_open_session = bool(display_session) and display_session == approval_session
    if routine_id and approval_session and not same_open_session:
        registry = getattr(request.app.state, "registry", None)
        kernel = getattr(request.app.state, "kernel", None)
        profile = registry.get_profile(agent_id) if registry else None
        if kernel and profile:
            try:
                resumed_msg = await kernel.run_turn(
                    agent=profile,
                    session_id=approval_session,
                    user_content=None,
                    resume=True,
                    approval_mode="ask",
                    routine_id=routine_id,
                )
                routine_resume = {
                    "ran": True,
                    "session_id": approval_session,
                    "content": getattr(resumed_msg, "content", "") or "",
                }
            except Exception:
                logger.exception("Routine HITL resume failed for %s", approval_id)
                routine_resume = {"ran": False, "session_id": approval_session}

    return {
        "status": decision_norm,
        "approval_id": approval_id,
        "execution": execution,
        "nested": nested,
        "routine_id": routine_id or None,
        "resumed": bool(routine_resume and routine_resume.get("ran")),
        "routine_resume": routine_resume,
    }


@router.get("/api/hitl/pending")
async def list_pending_actions(request: Request):
    """List all actions awaiting human approval [REQ-HITL-003]."""
    approval_manager = request.app.state.approval_manager
    return [a.model_dump() for a in approval_manager.list_pending()]


@router.post("/api/hitl/decide")
async def decide_pending_action(request: Request, req: Dict[str, Any]):
    """Submit an approval or rejection decision [REQ-HITL-003]."""
    approval_manager = request.app.state.approval_manager
    action_id = (req.get("action_id") or "").strip()
    status_str = (req.get("status") or "").strip().lower()
    reason = req.get("reason")

    if not action_id:
        raise HTTPException(status_code=400, detail="Field 'action_id' is required.")

    try:
        status_val = ApprovalStatus(status_str)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status_str}'. Must be one of: approved, rejected.",
        )

    if status_val not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
        raise HTTPException(
            status_code=400,
            detail="Status must be 'approved' or 'rejected'.",
        )

    try:
        decision = approval_manager.decide(action_id, status_val, reason=reason)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No pending action with id '{action_id}'.")

    return decision.model_dump()
