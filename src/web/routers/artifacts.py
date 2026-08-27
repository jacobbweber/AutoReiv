"""
Session Artifact Management & Promotion Router [REQ-ART-004].
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.application.skills.wiki_skill import WikiSkill
from src.application.skills.worker_skill import BatchWorkerSkill
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class ArtifactPinRequest(BaseModel):
    is_pinned: bool = True


class ArtifactPromoteRequest(BaseModel):
    wiki_slug: str
    title: Optional[str] = None
    category: str = "reports"
    domain: str = "general"


router = APIRouter(tags=["Artifacts"])


def _get_state_store(request: Request) -> SQLiteStateStore:
    store = getattr(request.app.state, "state_store", None) or getattr(request.app.state, "store", None)
    if store:
        return store
    raise HTTPException(status_code=500, detail="State store not initialized")


def _get_worker_skill(request: Request) -> BatchWorkerSkill:
    store = _get_state_store(request)
    wiki_path = getattr(request.app.state, "wiki_path", "data/wiki")
    wiki_skill = WikiSkill(wiki_root=wiki_path)
    return BatchWorkerSkill(state_store=store, wiki_skill=wiki_skill)


@router.get("/api/sessions/{session_id}/artifacts")
async def list_session_artifacts(session_id: str, request: Request):
    store = _get_state_store(request)
    artifacts = store.list_session_artifacts(session_id)
    return {
        "success": True,
        "session_id": session_id,
        "artifacts": [
            {
                "id": a.id,
                "session_id": a.session_id,
                "title": a.title,
                "content_type": a.content_type,
                "summary": a.summary,
                "item_count": a.item_count,
                "is_pinned": a.is_pinned,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in artifacts
        ],
    }


@router.get("/api/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, request: Request):
    store = _get_state_store(request)
    art = store.get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")
    return {
        "success": True,
        "artifact": {
            "id": art.id,
            "session_id": art.session_id,
            "title": art.title,
            "content_type": art.content_type,
            "content": art.content,
            "summary": art.summary,
            "item_count": art.item_count,
            "is_pinned": art.is_pinned,
            "expires_at": art.expires_at.isoformat() if art.expires_at else None,
            "created_at": art.created_at.isoformat() if art.created_at else None,
        },
    }


@router.post("/api/artifacts/{artifact_id}/pin")
async def pin_artifact(artifact_id: str, payload: ArtifactPinRequest, request: Request):
    store = _get_state_store(request)
    success = store.pin_artifact(artifact_id, is_pinned=payload.is_pinned)
    if not success:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")
    return {"success": True, "artifact_id": artifact_id, "is_pinned": payload.is_pinned}


@router.post("/api/artifacts/{artifact_id}/promote")
async def promote_artifact(artifact_id: str, payload: ArtifactPromoteRequest, request: Request):
    worker_skill = _get_worker_skill(request)
    result = worker_skill.promote_artifact_to_wiki(
        artifact_id=artifact_id,
        wiki_slug=payload.wiki_slug,
        title=payload.title,
        category=payload.category,
        domain=payload.domain,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Promotion failed"))
    return result


@router.delete("/api/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str, request: Request):
    store = _get_state_store(request)
    success = store.delete_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_id}' not found")
    return {"success": True, "artifact_id": artifact_id}
