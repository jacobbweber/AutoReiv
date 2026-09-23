"""Tools Studio Talk / Submit authoring API [CARD-422]."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.tools.developer_mediation import ToolsAuthoringError, ToolsDeveloperMediationService

router = APIRouter(prefix="/api/tools_studio/authoring", tags=["Tools Studio Authoring"])


class ToolIntentRequest(BaseModel):
    intent: str
    draft: dict[str, Any] = Field(default_factory=dict)


def _service(request: Request) -> ToolsDeveloperMediationService:
    store = getattr(request.app.state, "store", None)
    orchestrator = getattr(request.app.state, "job_orchestrator", None)
    registry = getattr(request.app.state, "registry", None)
    kernel = getattr(request.app.state, "kernel", None)
    if store is None:
        raise HTTPException(status_code=503, detail={"message": "Developer mediation is unavailable.", "ran": False})
    return ToolsDeveloperMediationService(store, orchestrator, registry, kernel)


def _http_error(exc: ToolsAuthoringError) -> HTTPException:
    detail = {"message": str(exc), "ran": False}
    detail.update(exc.extra)
    return HTTPException(status_code=exc.status_code, detail=detail)


async def _call(action):
    try:
        result = action()
        if inspect.isawaitable(result):
            return await result
        return result
    except ToolsAuthoringError as exc:
        raise _http_error(exc) from exc


@router.post("/talk")
async def talk_to_developer(payload: ToolIntentRequest, request: Request) -> dict[str, Any]:
    """Open a new developer chat that already contains the form context. Does not mint a job."""
    return await _call(lambda: _service(request).open_chat(payload.intent, payload.draft))


@router.post("/jobs")
async def submit_tool_intent(payload: ToolIntentRequest, request: Request) -> dict[str, Any]:
    """Run a developer turn for this tool intent, or refuse when mediation cannot run."""
    return await _call(lambda: _service(request).submit(payload.intent, payload.draft))


@router.get("/jobs/{job_id}")
def get_tool_authoring_job(job_id: str, request: Request) -> dict[str, Any]:
    try:
        return _service(request).get_job(job_id)
    except ToolsAuthoringError as exc:
        raise _http_error(exc) from exc
