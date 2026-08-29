"""
Human-In-The-Loop (HITL) Action Approval Router [REQ-SAFE-005, REQ-SAFE-006, REQ-HITL-003].
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.domain.gateway.models import ToolCall
from src.domain.hitl.models import ApprovalStatus


class DecisionRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    reason: Optional[str] = None


router = APIRouter(tags=["HITL"])


@router.get("/api/approvals/pending")
async def get_pending_approvals(request: Request):
    store = request.app.state.store
    return store.get_pending_approvals()


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
    if decision_norm in {"approved", "approve"} and record:
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

    return {
        "status": decision_norm,
        "approval_id": approval_id,
        "execution": execution,
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
