"""Skill Studio Build/Review authoring API [CARD-420]."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.skills.developer_authoring import AuthoringError, DeveloperAuthoringService
from src.application.skills.workshop import catalog_tool_ids

router = APIRouter(prefix="/api/skill_studio/authoring", tags=["Skill Studio Authoring"])


class AuthoringDraftRequest(BaseModel):
    draft: dict[str, Any] = Field(default_factory=dict)


class AuthoringJobRequest(BaseModel):
    intent: str
    draft: dict[str, Any] = Field(default_factory=dict)


class AuthoringProposalRequest(BaseModel):
    patches: list[dict[str, Any]] = Field(default_factory=list)


class AuthoringDecisionRequest(BaseModel):
    decision: str


def _service(request: Request) -> DeveloperAuthoringService:
    store = getattr(request.app.state, "store", None)
    orchestrator = getattr(request.app.state, "job_orchestrator", None)
    if store is None or orchestrator is None:
        raise HTTPException(status_code=503, detail="Authoring job store is unavailable.")
    registry = getattr(request.app.state, "tool_registry", None)
    return DeveloperAuthoringService(store, orchestrator, catalog_tool_ids(registry))


def _call(action):
    try:
        return action()
    except AuthoringError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/lint")
def lint_skill_draft(payload: AuthoringDraftRequest, request: Request) -> dict[str, Any]:
    """Cheap lint only. Does not open a developer job."""
    return _call(lambda: _service(request).lint(payload.draft))


@router.post("/jobs")
def submit_authoring_job(payload: AuthoringJobRequest, request: Request) -> dict[str, Any]:
    """Create or resume a visible developer standing job for this draft."""
    return _call(lambda: _service(request).submit(payload.intent, payload.draft))


@router.get("/jobs/{job_id}")
def get_authoring_job(job_id: str, request: Request) -> dict[str, Any]:
    return _call(lambda: _service(request).get_job(job_id))


@router.post("/jobs/{job_id}/proposals")
def propose_authoring_patches(
    job_id: str,
    payload: AuthoringProposalRequest,
    request: Request,
) -> dict[str, Any]:
    return _call(lambda: _service(request).propose(job_id, payload.patches))


@router.post("/jobs/{job_id}/decision")
def decide_authoring_patches(
    job_id: str,
    payload: AuthoringDecisionRequest,
    request: Request,
) -> dict[str, Any]:
    return _call(lambda: _service(request).decide(job_id, payload.decision))
