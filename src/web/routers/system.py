"""
System Health, Status, Updates & Episodic Facts Memory Router [REQ-EPISODIC-004, REQ-UPD-001..005].
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

from src.application.system.update_service import UpdateService
from src.domain.system.models import (
    SystemVersionInfo,
    UpdateApplyResult,
    UpdateCheckResult,
    UpdateConfig,
)

router = APIRouter(tags=["System"])


def _get_update_service(request: Request) -> UpdateService:
    if hasattr(request.app.state, "update_service") and request.app.state.update_service:
        return request.app.state.update_service
    store = getattr(request.app.state, "store", None)
    repo_root = getattr(request.app.state, "repo_root", None)
    data_dir = getattr(request.app.state, "data_dir", None)
    svc = UpdateService(state_store=store, repo_root=repo_root, data_dir=data_dir)
    request.app.state.update_service = svc
    return svc


@router.get("/health")
@router.get("/api/health")
async def health_check(request: Request):
    try:
        svc = _get_update_service(request)
        ver = svc.get_version_info().current_version
    except Exception:
        ver = "0.24.0"
    return {"status": "ok", "app": "AutoReiv", "version": ver}


@router.get("/api/system/version", response_model=SystemVersionInfo)
async def get_system_version(request: Request):
    """Retrieve installed version, git commit, branch, and runtime deployment mode [REQ-UPD-001]."""
    svc = _get_update_service(request)
    return svc.get_version_info()


@router.get("/api/system/updates/config", response_model=UpdateConfig)
async def get_update_config(request: Request):
    """Fetch persisted upstream repository URL and tracked branch [REQ-UPD-002]."""
    svc = _get_update_service(request)
    return svc.get_update_config()


@router.put("/api/system/updates/config", response_model=UpdateConfig)
async def save_update_config(request: Request, config: UpdateConfig):
    """Update and persist upstream repository settings in SQLite [REQ-UPD-002]."""
    svc = _get_update_service(request)
    return svc.save_update_config(config)


@router.get("/api/system/updates/check", response_model=UpdateCheckResult)
async def check_system_updates(request: Request, branch: Optional[str] = None):
    """Query upstream remote or GitHub API for available updates [REQ-UPD-003]."""
    svc = _get_update_service(request)
    return svc.check_for_updates(override_branch=branch)


@router.post("/api/system/updates/apply", response_model=UpdateApplyResult)
async def apply_system_update(request: Request):
    """Execute safe update with dirty tree check and database snapshot [REQ-UPD-004, REQ-UPD-005]."""
    svc = _get_update_service(request)
    return svc.apply_update()


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
