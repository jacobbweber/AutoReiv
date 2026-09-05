"""
Capability Gaps API Router [REQ-FACT-027, REQ-FACT-028].
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.domain.orchestration.factory_packets import FactoryJob
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

router = APIRouter(prefix="/api/agents", tags=["Capability Gaps"])


class CreateGapRequest(BaseModel):
    turn_text: str
    identified_capability: str
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


def _factory_repo(request: Request) -> FactoryPacketRepository:
    repo = getattr(request.app.state, "factory_repo", None)
    if repo is None:
        store = getattr(request.app.state, "state_store", None)
        conn_mgr = getattr(store, "connection_manager", None) if store else None
        repo = FactoryPacketRepository(connection_manager=conn_mgr)
        request.app.state.factory_repo = repo
    return repo


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
    gap = repo.create_gap(
        agent_id=agent_id,
        turn_text=payload.turn_text,
        identified_capability=payload.identified_capability,
        suggested_tool_name=payload.suggested_tool_name,
        session_id=payload.session_id,
    )
    return {
        "success": True,
        "gap": gap.model_dump(),
    }


@router.post("/{agent_id}/gaps/{gap_id}/train")
async def train_gap_in_lab(agent_id: str, gap_id: str, request: Request) -> Dict[str, Any]:
    gap_repo = _gap_repo(request)
    gap = gap_repo.get_gap(gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail=f"Capability gap '{gap_id}' not found.")

    # Create factory training job anchored to AutoReiv session
    factory_repo = _factory_repo(request)
    store = getattr(request.app.state, "state_store", None)

    session_id = None
    if store is not None:
        autoreiv_sessions = store.list_sessions(agent_id="autoreiv")
        if autoreiv_sessions:
            session_id = autoreiv_sessions[0].id
        else:
            new_sess = store.create_session(agent_id="autoreiv", title="AutoReiv Control Plane")
            session_id = new_sess.id

    if not session_id:
        session_id = f"sess_factory_{uuid.uuid4().hex[:8]}"

    job_id = f"fjob_{uuid.uuid4().hex[:12]}"
    job = FactoryJob(
        id=job_id,
        target_agent_id=agent_id,
        session_id=session_id,
        status="queued",
        seed_intent=f"{gap.identified_capability} (from turn: '{gap.turn_text}')",
        active_graph_id="graph_standard_factory_v1",
        current_node_id="discovery_probe",
    )
    factory_repo.save_job(job)

    # Step immediately if factory_runner is active
    runner = getattr(request.app.state, "factory_runner", None)
    if runner and hasattr(runner, "step_job"):
        try:
            await runner.step_job(job_id)
        except Exception:
            pass

    # Mark gap as trained
    gap_repo.update_gap_status(gap_id, "trained")

    return {
        "success": True,
        "job_id": job_id,
        "gap_id": gap_id,
        "status": "queued",
    }


@router.delete("/{agent_id}/gaps/{gap_id}")
async def dismiss_agent_gap(agent_id: str, gap_id: str, request: Request) -> Dict[str, Any]:
    repo = _gap_repo(request)
    gap = repo.get_gap(gap_id)
    if not gap:
        raise HTTPException(status_code=404, detail=f"Capability gap '{gap_id}' not found.")
    repo.update_gap_status(gap_id, "dismissed")
    return {
        "success": True,
        "gap_id": gap_id,
        "status": "dismissed",
    }
