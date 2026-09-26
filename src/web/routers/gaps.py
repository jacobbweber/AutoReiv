"""
Capability Gaps API Router [REQ-FACT-027, REQ-FACT-028].

Create, list and dismiss. A gap opens Skill Studio or a Developer chat in the UI; the
Factory train route is gone [CARD-496, CARD-497].
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.orchestration.capability_detector import CapabilityDetector
from src.infrastructure.memory.repositories.capability_gaps import GAP_DISMISSED, CapabilityGapRepository

router = APIRouter(prefix="/api/agents", tags=["Capability Gaps"])


class CreateGapRequest(BaseModel):
    turn_text: Optional[str] = None
    user_prompt: Optional[str] = None
    assistant_response: Optional[str] = None
    context_summary: Optional[str] = None
    identified_capability: Optional[str] = None
    suggested_tool_name: Optional[str] = None
    session_id: Optional[str] = None


def _gap_repo(request: Request) -> CapabilityGapRepository:
    repo = getattr(request.app.state, "capability_gap_repo", None)
    if repo is None:
        store = getattr(request.app.state, "state_store", None)
        conn_mgr = getattr(store, "connection_manager", None) if store else None
        repo = CapabilityGapRepository(connection_manager=conn_mgr)
        request.app.state.capability_gap_repo = repo
    return repo


@router.get("/gaps")
async def list_all_gaps(request: Request, status: Optional[str] = "pending") -> Dict[str, Any]:
    repo = _gap_repo(request)
    gaps = repo.list_gaps(agent_id=None, status=status)
    return {
        "success": True,
        "agent_id": None,
        "gaps": [g.model_dump() for g in gaps],
    }


@router.get("/{agent_id}/gaps")
async def list_agent_gaps(agent_id: str, request: Request, status: Optional[str] = "pending") -> Dict[str, Any]:
    repo = _gap_repo(request)
    gaps = repo.list_gaps(agent_id=agent_id, status=status)
    return {
        "success": True,
        "agent_id": agent_id,
        "gaps": [g.model_dump() for g in gaps],
    }


@router.post("/{agent_id}/gaps")
async def create_agent_gap(agent_id: str, payload: CreateGapRequest, request: Request) -> Dict[str, Any]:
    repo = _gap_repo(request)

    prompt = (payload.user_prompt or payload.turn_text or "").strip()
    resp = (payload.assistant_response or payload.context_summary or "").strip()

    # Look up agent profile name if available
    registry = getattr(request.app.state, "registry", None)
    agent_name = ""
    if registry and hasattr(registry, "get_agent"):
        profile = registry.get_agent(agent_id)
        if profile:
            agent_name = profile.name

    cap = (payload.identified_capability or "").strip()
    tool_name = payload.suggested_tool_name
    turn_text = payload.turn_text or prompt

    # If capability was not explicitly supplied or is generic, synthesize it
    if not cap or cap.lower() in ("user flagged missing capability", "missing capability", ""):
        gateway = getattr(request.app.state, "gateway", None)
        synthesis = await CapabilityDetector.analyze_turn_with_llm(
            user_prompt=prompt,
            assistant_response=resp,
            agent_id=agent_id,
            agent_name=agent_name,
            gateway=gateway,
        )
        cap = synthesis.get("identified_capability") or f"{agent_name or agent_id.capitalize()} Capability"
        tool_name = tool_name or synthesis.get("suggested_tool_name")
        turn_text = synthesis.get("turn_text") or prompt

    gap = repo.create_gap(
        agent_id=agent_id,
        turn_text=turn_text,
        identified_capability=cap,
        suggested_tool_name=tool_name,
        session_id=payload.session_id,
    )
    return {
        "success": True,
        "gap": gap.model_dump(),
    }


@router.delete("/{agent_id}/gaps/{gap_id}")
async def dismiss_agent_gap(agent_id: str, gap_id: str, request: Request) -> Dict[str, Any]:
    repo = _gap_repo(request)
    gap = repo.get_gap(gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail=f"Capability gap '{gap_id}' not found.")
    repo.update_gap_status(gap_id, GAP_DISMISSED)
    return {
        "success": True,
        "gap_id": gap_id,
        "status": GAP_DISMISSED,
    }
