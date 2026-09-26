"""
System Health, Status, Updates & Episodic Facts Memory Router
[REQ-EPISODIC-004, REQ-UPD-001..005, CARD-451 REQ-451-001..017].
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.system.busy import make_store_busy_detector
from src.application.system.serve_restarter import DetachedScriptRestarter
from src.application.system.update_service import UpdateService
from src.domain.system.models import (
    AutoUpdateStatus,
    BranchListResult,
    SwitchBranchResult,
    SystemVersionInfo,
    UpdateApplyResult,
    UpdateCheckResult,
    UpdateConfig,
    UpdateHistoryResult,
)

router = APIRouter(tags=["System"])


class SwitchBranchRequest(BaseModel):
    branch: str = Field(..., min_length=1, max_length=200)


def _get_update_service(request: Request) -> UpdateService:
    if hasattr(request.app.state, "update_service") and request.app.state.update_service:
        return request.app.state.update_service

    store = request.app.state.store
    repo_root = getattr(request.app.state, "repo_root", None)
    data_dir = None
    if getattr(request.app.state, "data_dir_paths", None) is not None:
        data_dir = str(request.app.state.data_dir_paths.root)
    busy = make_store_busy_detector(store)
    restarter = getattr(request.app.state, "serve_restarter", None) or DetachedScriptRestarter()
    serve_host = getattr(request.app.state, "serve_host", None)
    serve_port = getattr(request.app.state, "serve_port", None)
    svc = UpdateService(
        state_store=store,
        repo_root=repo_root,
        data_dir=data_dir,
        restarter=restarter,
        busy_detector=busy,
        serve_host=serve_host,
        serve_port=serve_port,
    )
    request.app.state.update_service = svc
    return svc


@router.get("/health")
@router.get("/api/health")
async def health(request: Request):
    ver = "unknown"
    try:
        svc = _get_update_service(request)
        ver = svc.get_version_info().current_version
    except Exception:
        pass
    return {"status": "ok", "app": "AutoReiv", "version": ver}


@router.get("/api/system/version", response_model=SystemVersionInfo)
async def get_system_version(request: Request):
    """Retrieve installed version, git commit, branch, ahead/behind [REQ-451-001]."""
    svc = _get_update_service(request)
    return svc.get_version_info()


@router.get("/api/system/updates/config", response_model=UpdateConfig)
async def get_update_config(request: Request):
    svc = _get_update_service(request)
    return svc.get_update_config()


@router.put("/api/system/updates/config", response_model=UpdateConfig)
async def save_update_config(request: Request, config: UpdateConfig):
    """Persist auto-update preferences (fixed origin; no remote URL) [REQ-451-007, REQ-451-016]."""
    svc = _get_update_service(request)
    return svc.save_update_config(config)


@router.get("/api/system/updates/check", response_model=UpdateCheckResult)
async def check_system_updates(request: Request, branch: Optional[str] = None):
    """git fetch --prune origin then refresh status [REQ-451-002]. branch query ignored."""
    del branch
    svc = _get_update_service(request)
    return svc.check_for_updates()


@router.post("/api/system/updates/apply", response_model=UpdateApplyResult)
async def apply_system_update(request: Request):
    """Fast-forward current branch upstream; restart after success [REQ-451-003..006]."""
    svc = _get_update_service(request)
    return svc.apply_update(trigger="manual")


@router.get("/api/system/updates/branches", response_model=BranchListResult)
async def list_update_branches(request: Request):
    """List local + origin remote branches for the picker [REQ-451-005]."""
    svc = _get_update_service(request)
    return svc.list_branches()


@router.post("/api/system/updates/switch", response_model=SwitchBranchResult)
async def switch_update_branch(request: Request, body: SwitchBranchRequest):
    """Switch to a listed branch (create tracking from origin if needed) [REQ-451-005]."""
    svc = _get_update_service(request)
    return svc.switch_branch(body.branch)


@router.get("/api/system/updates/history", response_model=UpdateHistoryResult)
async def get_update_history(request: Request, limit: int = 20):
    """Recent update/switch history from user-data settings [REQ-451-008]."""
    svc = _get_update_service(request)
    return svc.get_history(limit=min(max(limit, 1), 50))


@router.get("/api/system/updates/auto-status", response_model=AutoUpdateStatus)
async def get_auto_update_status(request: Request):
    """Last daily auto-update outcome [REQ-451-007]."""
    svc = _get_update_service(request)
    return svc.get_auto_update_status()


@router.get("/api/memory/facts")
async def list_or_search_facts(
    request: Request,
    q: Optional[str] = None,
    entity: Optional[str] = None,
    min_confidence: float = 0.5,
    limit: int = 50,
):
    store = request.app.state.store
    if q:
        return store.search_facts(query=q, entity=entity, min_confidence=min_confidence, limit=limit)
    return store.get_facts(entity=entity)[:limit]


@router.post("/api/memory/facts")
async def create_or_update_fact(request: Request, req: Dict[str, Any]):
    store = request.app.state.store
    entity = (req.get("entity") or "").strip()
    key = (req.get("key") or "").strip()
    value = str(req.get("value") or "").strip()
    if not entity or not key:
        raise HTTPException(status_code=400, detail="Fields 'entity' and 'key' are required.")
    confidence = float(req.get("confidence", 1.0))
    source_session_id = req.get("source_session_id")
    fact = store.save_fact(
        entity=entity,
        key=key,
        value=value,
        confidence=confidence,
        source_session_id=source_session_id,
    )
    return {"status": "saved", "fact": fact}


@router.delete("/api/memory/facts/{entity}/{key}")
async def delete_episodic_fact(request: Request, entity: str, key: str):
    store = request.app.state.store
    deleted = store.delete_fact(entity=entity, key=key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Fact '{entity}.{key}' not found.")
    return {"status": "deleted", "entity": entity, "key": key}
