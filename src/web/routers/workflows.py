"""
Workflow recipe API [CARD-123].
Recipes live on the starting agent. Chat picker lists that agent's startable recipes.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.orchestration.workflow_service import (
    instantiate_workflow,
    save_job_as_workflow,
)
from src.domain.orchestration.models import utc_now
from src.domain.orchestration.workflow import Workflow, WorkflowChapter
from src.infrastructure.memory.repositories.workflows import WorkflowStore, new_workflow_id, safe_id

router = APIRouter(tags=["Workflows"])


class SaveFromJobRequest(BaseModel):
    name: str
    job_id: str
    session_id: Optional[str] = None


class WorkflowChapterPayload(BaseModel):
    name: str
    kind: str = "skill"
    assigned_agent_id: str = ""
    skill_id: Optional[str] = None
    handoff_target_agent_id: Optional[str] = None
    success_rule: str = ""


class WorkflowWriteRequest(BaseModel):
    name: str
    chapters: List[WorkflowChapterPayload] = Field(default_factory=list)


def _store(request: Request) -> WorkflowStore:
    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        raise HTTPException(status_code=500, detail="Data directory is not configured.")
    packs_path = getattr(paths, "packs_path", paths.root / "packs")
    agents_path = getattr(paths, "agents_path", paths.root / "agents")
    return WorkflowStore(packs_path=packs_path, legacy_agents_path=agents_path)


def _require_agent(request: Request, agent_id: str) -> None:
    registry = request.app.state.registry
    profile = registry.get_agent(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")


def _as_public(workflow: Workflow) -> Dict[str, Any]:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "owner_agent_id": workflow.owner_agent_id,
        "chapters": [c.model_dump() for c in workflow.chapters],
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


@router.get("/api/agents/{agent_id}/workflows")
async def list_workflows(request: Request, agent_id: str):
    _require_agent(request, agent_id)
    items = _store(request).list_for_agent(agent_id)
    return [_as_public(item) for item in items]


@router.post("/api/agents/{agent_id}/workflows/from-job")
async def save_workflow_from_job(request: Request, agent_id: str, payload: SaveFromJobRequest):
    _require_agent(request, agent_id)
    store = request.app.state.store
    try:
        job = store.get_job(payload.job_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Job '{payload.job_id}' not found.") from exc
    if job.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Job is not owned by this agent.")
    phases = store.list_phases_for_job(job.id)
    try:
        workflow = save_job_as_workflow(
            _store(request),
            job,
            phases,
            payload.name,
            owner_agent_id=agent_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "workflow": _as_public(workflow)}


@router.get("/api/agents/{agent_id}/workflows/{workflow_id}")
async def get_workflow(request: Request, agent_id: str, workflow_id: str):
    _require_agent(request, agent_id)
    item = _store(request).get(agent_id, workflow_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return _as_public(item)


@router.post("/api/agents/{agent_id}/workflows")
async def create_workflow(request: Request, agent_id: str, payload: WorkflowWriteRequest):
    _require_agent(request, agent_id)
    try:
        safe_id(agent_id)
        chapters = [WorkflowChapter.model_validate(c.model_dump()) for c in payload.chapters]
        now = utc_now()
        workflow = Workflow(
            id=new_workflow_id(),
            name=(payload.name or "").strip(),
            owner_agent_id=agent_id,
            chapters=chapters,
            created_at=now,
            updated_at=now,
        )
        if not workflow.name:
            raise ValueError("Workflow name is required.")
        saved = _store(request).save(workflow)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "created", "workflow": _as_public(saved)}


@router.put("/api/agents/{agent_id}/workflows/{workflow_id}")
async def update_workflow(request: Request, agent_id: str, workflow_id: str, payload: WorkflowWriteRequest):
    _require_agent(request, agent_id)
    store = _store(request)
    existing = store.get(agent_id, workflow_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    try:
        chapters = [WorkflowChapter.model_validate(c.model_dump()) for c in payload.chapters]
        existing.name = (payload.name or "").strip() or existing.name
        existing.chapters = chapters
        existing.updated_at = utc_now()
        saved = store.save(existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "updated", "workflow": _as_public(saved)}


@router.delete("/api/agents/{agent_id}/workflows/{workflow_id}")
async def delete_workflow(request: Request, agent_id: str, workflow_id: str):
    _require_agent(request, agent_id)
    if not _store(request).delete(agent_id, workflow_id):
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    return {"status": "deleted", "id": workflow_id}


@router.post("/api/agents/{agent_id}/workflows/{workflow_id}/instantiate")
async def instantiate_workflow_endpoint(
    request: Request,
    agent_id: str,
    workflow_id: str,
    payload: Dict[str, Any],
):
    """Create a Job + Phase rows from the recipe. Used by tests and Chat."""
    _require_agent(request, agent_id)
    orch = getattr(request.app.state, "job_orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=500, detail="Job orchestrator is not configured.")
    goal = str((payload or {}).get("goal") or "").strip()
    session_id = str((payload or {}).get("session_id") or "").strip()
    if not goal:
        raise HTTPException(status_code=422, detail="goal is required.")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id is required.")
    try:
        job = instantiate_workflow(
            _store(request),
            orch,
            owner_agent_id=agent_id,
            workflow_id=workflow_id,
            goal=goal,
            session_id=session_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    store = request.app.state.store
    phases = store.list_phases_for_job(job.id)
    return {
        "job_id": job.id,
        "template_id": job.template_id,
        "goal": job.goal,
        "agent_id": job.agent_id,
        "session_id": job.session_id,
        "phases": [
            {
                "id": p.id,
                "name": p.name,
                "index": p.index,
                "assigned_agent_id": p.assigned_agent_id,
                "success_rule": p.success_rule,
            }
            for p in phases
        ],
    }
