"""
Factory Training Loop API Router [REQ-FACT-003, REQ-FACT-005, REQ-FACT-012, REQ-FACT-014].

Provides REST endpoints for launching training jobs, retrieving status/eval packets,
and promoting certified agent packs to live deployment.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.orchestration.capability_graph import UserPackFinalizer
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket, WorkPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository

router = APIRouter(prefix="/api/factory", tags=["Factory"])


class CreateFactoryJobRequest(BaseModel):
    target_agent_id: str = Field(description="Slug for new agent pack")
    seed_intent: str = Field(description="High-level description of agent purpose")
    target_host: Optional[str] = Field(default=None, description="Remote host / IP")
    target_directory: Optional[str] = Field(default=None, description="Target host directory")
    objectives: List[str] = Field(default_factory=list, description="Top starter objectives")
    risk_policy: str = Field(default="ask", description="Approval requirement policy")
    session_id: Optional[str] = Field(default=None, description="Originating chat session ID")


class PromoteJobRequest(BaseModel):
    decision: str = Field(default="approved", description="approved | rejected")


def _repo(request: Request) -> FactoryPacketRepository:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Database store not available")
    return FactoryPacketRepository(store)


@router.post("/jobs")
async def create_factory_job(payload: CreateFactoryJobRequest, request: Request) -> Dict[str, Any]:
    repo = _repo(request)
    session_id = payload.session_id or f"sess_factory_{uuid.uuid4().hex[:8]}"

    job_id = f"fjob_{uuid.uuid4().hex[:12]}"
    job = FactoryJob(
        id=job_id,
        target_agent_id=payload.target_agent_id,
        session_id=session_id,
        status="queued",
        seed_intent=payload.seed_intent,
        target_host=payload.target_host,
        active_graph_id="graph_standard_factory_v1",
        current_node_id="discovery_probe",
    )
    repo.save_job(job)

    # Initial WorkPacket
    work_pkt = WorkPacket(
        goal=payload.seed_intent,
        target_agent_id=payload.target_agent_id,
        facts=payload.objectives,
        constraints=[f"risk_policy={payload.risk_policy}"],
        done_when="Seed objectives verified in sandbox battery",
        target_host=payload.target_host,
        target_directory=payload.target_directory,
    )
    envelope = FactoryPacket(
        id=f"fpkt_{uuid.uuid4().hex[:12]}",
        job_id=job_id,
        packet_type="work",
        sender_role="conductor",
        recipient_role="inspector",
        node_id="discovery_probe",
        payload=work_pkt.model_dump(),
    )
    repo.save_packet(envelope)

    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "current_node_id": job.current_node_id,
        "target_agent_id": job.target_agent_id,
    }


@router.get("/jobs")
async def list_factory_jobs(request: Request, status: Optional[str] = None) -> Dict[str, Any]:
    repo = _repo(request)
    jobs = repo.list_jobs(status=status)
    return {
        "success": True,
        "jobs": [j.model_dump() for j in jobs],
    }


@router.get("/jobs/{job_id}")
async def get_factory_job(job_id: str, request: Request) -> Dict[str, Any]:
    repo = _repo(request)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")

    packets = repo.list_packets(job_id)
    eval_runs = repo.list_eval_runs(job_id)

    return {
        "success": True,
        "job": job.model_dump(),
        "packets": [p.model_dump() for p in packets],
        "eval_runs": [e.model_dump() for e in eval_runs],
    }


@router.post("/jobs/{job_id}/promote")
async def promote_factory_job(job_id: str, request: Request, payload: Optional[PromoteJobRequest] = None) -> Dict[str, Any]:
    repo = _repo(request)
    job = repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")

    decision = payload.decision if payload else "approved"
    if decision != "approved":
        repo.update_job_status(job_id, "failed", current_node_id="rejected")
        return {"success": True, "job_id": job_id, "status": "failed"}

    # Finalize pack
    data_paths = getattr(request.app.state, "data_dir_paths", None)
    data_dir = str(data_paths.root) if data_paths else "./data"
    finalizer = UserPackFinalizer(data_dir=data_dir)

    manifest_data = {
        "id": job.target_agent_id,
        "name": job.target_agent_id.replace("-", " ").title(),
        "description": job.seed_intent,
        "system_prompt": f"You are a specialist agent trained for: {job.seed_intent}",
        "tone": "concise",
        "show_in_chat": True,
    }

    pack_dir = finalizer.finalize_pack(
        agent_id=job.target_agent_id,
        manifest_data=manifest_data,
        files={},
    )

    repo.update_job_status(job_id, "done", current_node_id="pack_finalized_node")

    return {
        "success": True,
        "job_id": job_id,
        "agent_id": job.target_agent_id,
        "status": "done",
        "pack_dir": pack_dir,
    }
