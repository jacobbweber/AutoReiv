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

# --- Self-Scaffold Spine [CARD-218] ---


class ScaffoldDraftRequest(BaseModel):
    kind: str
    name: str = Field(..., min_length=1)
    pack_id: str = Field(..., min_length=1)
    summary: str = ""
    content: str = ""
    proposal_id: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    skip_disk_write: bool = False


class ScaffoldSandboxRequest(BaseModel):
    evidence: str = "sandbox_ok"


class ScaffoldWriteTrustedRequest(BaseModel):
    kind: str = "skill"
    name: str = Field(..., min_length=1)
    pack_id: str = Field(..., min_length=1)
    content: str = ""
    summary: str = ""


def _spine(request: Request):
    existing = getattr(request.app.state, "scaffold_spine", None)
    if existing is not None:
        return existing
    from pathlib import Path

    from src.application.capabilities.scaffold_spine import SelfScaffoldSpine
    from src.application.skills.user_catalog import UserSkillCatalog
    from src.infrastructure.memory.repositories.scaffold_spine import ScaffoldSpineRepository

    store = request.app.state.store
    data_dir = getattr(request.app.state, "data_dir", None)
    if data_dir is None:
        settings = getattr(request.app.state, "settings", None)
        data_dir = getattr(settings, "data_dir", None) if settings else None
    skills_dir = Path(data_dir) / "skills" if data_dir else Path("data") / "skills"
    cap_repo = getattr(request.app.state, "capability_catalog_repo", None)
    if cap_repo is None:
        cap_repo = CapabilityCatalogRepository(store)
        request.app.state.capability_catalog_repo = cap_repo
    catalog = getattr(request.app.state, "user_skill_catalog", None)
    if catalog is None:
        catalog = UserSkillCatalog(skills_dir=skills_dir)
        request.app.state.user_skill_catalog = catalog
    spine = SelfScaffoldSpine(
        spine_repo=ScaffoldSpineRepository(store),
        capability_repo=cap_repo,
        catalog=catalog,
    )
    request.app.state.scaffold_spine = spine
    return spine


@router.post("/api/capabilities/scaffold/draft")
async def scaffold_draft(request: Request, body: ScaffoldDraftRequest):
    """Draft a candidate skill/tool (never trusted by default) [REQ-SCAFFOLD-001]."""
    from src.application.capabilities.scaffold_spine import CandidateUnsandboxedError

    spine = _spine(request)
    try:
        rec = spine.draft(
            kind=body.kind,
            name=body.name,
            pack_id=body.pack_id,
            summary=body.summary,
            content=body.content,
            proposal_id=body.proposal_id,
            keywords=body.keywords,
            skip_disk_write=body.skip_disk_write,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CandidateUnsandboxedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"record": rec.model_dump(mode="json")}


@router.get("/api/capabilities/scaffold/candidates")
async def scaffold_candidates(request: Request, limit: int = 50):
    """Agent Forge candidate queue [REQ-SCAFFOLD-007]."""
    spine = _spine(request)
    rows = spine.list_candidates(limit=limit)
    return {
        "candidates": [r.model_dump(mode="json") for r in rows],
        "count": len(rows),
        "forge_queue": True,
    }


@router.post("/api/capabilities/scaffold/{record_id}/sandbox")
async def scaffold_sandbox(request: Request, record_id: str, body: ScaffoldSandboxRequest):
    spine = _spine(request)
    try:
        rec = spine.mark_sandbox_exec(record_id, evidence=body.evidence)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"record": rec.model_dump(mode="json")}


@router.post("/api/capabilities/scaffold/{record_id}/version")
async def scaffold_version(request: Request, record_id: str):
    from src.application.capabilities.scaffold_spine import CandidateUnsandboxedError

    spine = _spine(request)
    try:
        rec = spine.version(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CandidateUnsandboxedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"record": rec.model_dump(mode="json")}


@router.post("/api/capabilities/scaffold/{record_id}/approve")
async def scaffold_approve(request: Request, record_id: str):
    from src.application.capabilities.scaffold_spine import CandidateUnsandboxedError

    spine = _spine(request)
    try:
        rec = spine.hitl_approve(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CandidateUnsandboxedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"record": rec.model_dump(mode="json")}


@router.post("/api/capabilities/scaffold/{record_id}/rollback")
async def scaffold_rollback(request: Request, record_id: str):
    spine = _spine(request)
    try:
        result = spine.rollback(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "rollback failed")
    return result


@router.post("/api/capabilities/scaffold/{record_id}/assert-run")
async def scaffold_assert_run(request: Request, record_id: str):
    """Run gate: candidate cannot run unsandboxed [REQ-SCAFFOLD-003]."""
    from src.application.capabilities.scaffold_spine import CandidateUnsandboxedError

    spine = _spine(request)
    try:
        return spine.assert_can_run(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CandidateUnsandboxedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/capabilities/scaffold/write-trusted")
async def scaffold_write_trusted_rejected(request: Request, body: ScaffoldWriteTrustedRequest):
    """Unscoped trusted write always rejected [REQ-SCAFFOLD-005]."""
    from src.application.capabilities.scaffold_spine import UnscopedTrustedWriteError

    spine = _spine(request)
    try:
        spine.write_trusted_unscoped(
            kind=body.kind,
            name=body.name,
            pack_id=body.pack_id,
            content=body.content,
            summary=body.summary,
        )
    except UnscopedTrustedWriteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=500, detail="unscoped trusted write must reject")
