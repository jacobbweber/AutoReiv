"""
Capability Catalog C API [CARD-217 / REQ-CAPCAT-003..006].

Match-only resolve + capped operator registry. No dump-all-for-prompt endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.capabilities.resolver import CapabilityCatalogResolver
from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    RiskLevel,
    TrustTier,
)
from src.infrastructure.memory.repositories.capability_catalog import CapabilityCatalogRepository

router = APIRouter(tags=["Capabilities"])


class ResolveRequest(BaseModel):
    intent: str = ""
    role: Optional[str] = None
    kinds: Optional[List[str]] = None
    limit: int = Field(default=12, ge=1, le=32)


class UpsertRequest(BaseModel):
    id: str = Field(..., min_length=1)
    kind: str
    name: str = Field(..., min_length=1)
    summary: str = ""
    keywords: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    trust_tier: Optional[str] = None
    risk_level: str = RiskLevel.MEDIUM.value
    requires_hitl: bool = False
    source: str = "self_authored"
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _resolver(request: Request) -> CapabilityCatalogResolver:
    existing = getattr(request.app.state, "capability_catalog", None)
    if existing is not None:
        return existing
    store = request.app.state.store
    repo = CapabilityCatalogRepository(store)
    resolver = CapabilityCatalogResolver(repo)
    request.app.state.capability_catalog = resolver
    request.app.state.capability_catalog_repo = repo
    return resolver


@router.post("/api/capabilities/resolve")
async def resolve_capabilities(request: Request, body: ResolveRequest):
    """Return matched capability subset only [REQ-CAPCAT-003]."""
    resolver = _resolver(request)
    try:
        result = resolver.resolve(
            body.intent,
            role=body.role,
            kinds=body.kinds,
            limit=body.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.as_dict()


@router.get("/api/capabilities/registry")
async def get_capability_registry(
    request: Request,
    kind: Optional[str] = None,
    trust_tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Capped operator/Observability registry view - not a prompt dump [REQ-CAPCAT-004/006]."""
    resolver = _resolver(request)
    kinds = [kind] if kind else None
    try:
        if kinds:
            for k in kinds:
                CapabilityKind(str(k).lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown capability kind (fail closed): {kind!r}") from exc
    return resolver.list_for_operator(
        kinds=kinds,
        trust_tier=trust_tier,
        limit=limit,
        offset=offset,
    )


@router.post("/api/capabilities/registry")
async def upsert_capability(request: Request, body: UpsertRequest):
    """Upsert an index entry. Self-authored defaults to candidate unless trust_tier set for builtins."""
    resolver = _resolver(request)
    try:
        kind = CapabilityKind(body.kind.strip().lower())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown capability kind (fail closed): {body.kind!r}") from exc

    source = (body.source or "self_authored").strip() or "self_authored"
    if source == "self_authored" and not body.trust_tier:
        entry = CapabilityIndexEntry.self_authored(
            id=body.id,
            kind=kind,
            name=body.name,
            summary=body.summary,
            keywords=body.keywords,
            roles=body.roles,
            risk_level=body.risk_level,
            requires_hitl=body.requires_hitl,
            metadata=body.metadata,
        )
    else:
        tier = TrustTier((body.trust_tier or TrustTier.CANDIDATE.value).strip().lower())
        entry = CapabilityIndexEntry(
            id=body.id,
            kind=kind,
            name=body.name,
            summary=body.summary,
            keywords=body.keywords,
            roles=body.roles,
            trust_tier=tier,
            risk_level=body.risk_level,
            requires_hitl=body.requires_hitl,
            source=source,
            metadata=body.metadata,
        )
    saved = resolver.upsert(entry)
    return {"entry": saved.model_dump(mode="json")}
