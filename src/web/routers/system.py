"""
System Health, Status & Episodic Facts Memory Router [REQ-EPISODIC-004].
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["System"])


@router.get("/health")
@router.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "AutoReiv", "version": "0.9.0"}


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
        return store.search_facts(
            query=q, entity=entity, min_confidence=min_confidence, limit=limit
        )
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
