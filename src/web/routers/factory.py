"""
Factory Training Loop API Router [REQ-FACT-003, REQ-FACT-005, REQ-FACT-012, REQ-FACT-014].

Provides REST endpoints for launching training jobs, retrieving status/eval packets,
and promoting certified agent packs to live deployment.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.orchestration.capability_graph import UserPackFinalizer
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
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
    store = getattr(request.app.state, "store", None)
    session_id = payload.session_id

    # Anchor training jobs to the AutoReiv platform supervisor session [REQ-FACT-018]
    if store is not None:
        if session_id:
            existing = store.get_session(session_id)
            if not existing or existing.agent_id != "autoreiv":
                autoreiv_sessions = store.list_sessions(agent_id="autoreiv")
                if autoreiv_sessions:
                    session_id = autoreiv_sessions[0].id
                else:
                    new_sess = store.create_session(agent_id="autoreiv", title="AutoReiv Control Plane")
                    session_id = new_sess.id
        else:
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

    # Immediately trigger runner tick if runner is active [REQ-FACT-016]
    runner = getattr(request.app.state, "factory_runner", None)
    if runner is not None:
        import asyncio

        asyncio.create_task(runner.tick())

    return {
        "success": True,
        "job_id": job.id,
        "status": job.status,
        "current_node_id": job.current_node_id,
        "target_agent_id": job.target_agent_id,
        "session_id": job.session_id,
    }


@router.get("/jobs")
async def list_factory_jobs(request: Request, status: Optional[str] = None) -> Dict[str, Any]:
    repo = _repo(request)
    jobs = repo.list_jobs(status=status)
    out = []
    for j in jobs:
        d = j.model_dump()
        pkts = repo.list_packets(j.id)
        d["packets_count"] = len(pkts)
        d["latest_packet"] = pkts[-1].model_dump() if pkts else None
        out.append(d)
    return {
        "success": True,
        "jobs": out,
    }


@router.post("/jobs/{job_id}/step")
async def step_factory_job(job_id: str, request: Request) -> Dict[str, Any]:
    runner = getattr(request.app.state, "factory_runner", None)
    if not runner:
        raise HTTPException(status_code=500, detail="Factory runner not available")
    stepped = await runner.step_job(job_id)
    repo = _repo(request)
    job = repo.get_job(job_id)
    return {
        "success": True,
        "stepped": stepped,
        "job": job.model_dump() if job else None,
    }


@router.delete("/jobs/{job_id}")
async def delete_factory_job(job_id: str, request: Request) -> Dict[str, Any]:
    repo = _repo(request)
    deleted = repo.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Factory job {job_id} not found")
    return {"success": True, "job_id": job_id, "deleted": True}


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

    clean_slug = job.target_agent_id.replace("-", "_").lower()
    default_tool_name = f"manage_{clean_slug}"
    default_tool_file = f"tools/{default_tool_name}.py"
    default_skill_file = f"skills/{clean_slug}/SKILL.md"

    packets = repo.list_packets(job_id)
    files_to_write: Dict[str, str] = {}
    tool_names = []

    for p in packets:
        if p.payload:
            if "files_map" in p.payload and isinstance(p.payload["files_map"], dict):
                files_to_write.update(p.payload["files_map"])
            if "tool_name" in p.payload:
                tool_names.append(p.payload["tool_name"])

    if not files_to_write:
        synthesized_map = ToolSynthesizer.synthesize_tool(
            agent_id=job.target_agent_id,
            seed_intent=job.seed_intent,
            objectives=getattr(job, "objectives", []) or [],
            tool_name=default_tool_name,
        )
        files_to_write.update(synthesized_map)
        tool_names.append(default_tool_name)

    unique_tools = list(dict.fromkeys(tool_names))

    manifest_data = {
        "id": job.target_agent_id,
        "name": job.target_agent_id.replace("-", " ").title(),
        "description": job.seed_intent,
        "system_prompt": f"You are a specialist agent trained for: {job.seed_intent}",
        "tone": "concise",
        "show_in_chat": True,
        "pack_tool_names": unique_tools,
        "allowed_tool_names": unique_tools,
        "allowed_skill": [clean_slug],
        "skills": [
            {
                "id": clean_slug,
                "name": f"{job.target_agent_id.title()} Skill",
                "description": f"Capabilities for {job.target_agent_id}",
                "tools": unique_tools,
            }
        ],
    }

    pack_dir = finalizer.finalize_pack(
        agent_id=job.target_agent_id,
        manifest_data=manifest_data,
        files=files_to_write,
    )

    # Dynamically register newly finalized tool handlers in master tool registry
    tool_reg = getattr(request.app.state, "tool_registry", None)
    registry = getattr(request.app.state, "registry", None)

    for t_name in unique_tools:
        loaded_handler = None
        tool_py_path = Path(pack_dir) / f"tools/{t_name}.py"
        if tool_py_path.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"live_pack_{t_name}", str(tool_py_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, t_name):
                        loaded_handler = getattr(mod, t_name)
            except Exception:
                pass

        def _make_handler(tool_id: str, agent_id: str):
            def _handler(action: str = "status", **kwargs):
                return {"success": True, "action": action, "agent": agent_id, "tool": tool_id, "details": kwargs}
            return _handler

        handler = loaded_handler or _make_handler(t_name, job.target_agent_id)
        if tool_reg:
            tool_reg.register_tool(
                name=t_name,
                description=f"Automated capability tool for {job.target_agent_id}.",
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action to perform (e.g. status, list, create)"},
                    },
                },
                handler=handler,
            )
        if registry and getattr(registry, "master_tool_registry", None):
            registry.master_tool_registry.register_tool(
                name=t_name,
                description=f"Automated capability tool for {job.target_agent_id}.",
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "Action to perform (e.g. status, list, create)"},
                    },
                },
                handler=handler,
            )

    # Immediately import the promoted pack into the live agent registry and state store
    store = getattr(request.app.state, "state_store", None)
    if registry is not None and store is not None:
        from src.application.agent_packs.service import AgentPackService

        available = None
        if tool_reg and hasattr(tool_reg, "list_tools"):
            available = {t.name for t in tool_reg.list_tools()}
        service = AgentPackService(
            data_dir=Path(data_dir),
            agent_registry=registry,
            store=store,
            available_tools=available,
        )
        try:
            service.import_path(pack_dir)
        except Exception:
            pass

    repo.update_job_status(job_id, "done", current_node_id="pack_finalized_node")

    return {
        "success": True,
        "job_id": job_id,
        "agent_id": job.target_agent_id,
        "status": "done",
        "pack_dir": pack_dir,
    }
