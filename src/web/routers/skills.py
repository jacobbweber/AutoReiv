import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.application.skills.skill_curator import (
    archive_pack,
    delete_pack,
    list_archived_packs,
    read_archived_pack,
    unarchive_pack,
)
from src.application.skills.user_catalog import PackJailError, UserSkillCatalog

router = APIRouter(tags=["Skills"])


class UserPackWrite(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    instructions: str = ""


class UserPackCreate(BaseModel):
    id: str = Field(..., min_length=1)
    name: Optional[str] = None
    description: str = "User skill pack."


class UserPackArchive(BaseModel):
    confirm: bool = False


class UserPackDelete(BaseModel):
    confirm: bool = False
    confirm_seed: bool = False


def _catalog(request: Request) -> UserSkillCatalog:
    catalog = getattr(request.app.state, "user_skill_catalog", None)
    if catalog is None:
        paths = getattr(request.app.state, "data_dir_paths", None)
        skills_dir = getattr(paths, "skills_path", None) if paths else None
        catalog = UserSkillCatalog(skills_dir=skills_dir)
        request.app.state.user_skill_catalog = catalog
    return catalog


def _http_jail(exc: PackJailError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/api/skills/user-packs")
async def list_user_packs(request: Request, include_archived: bool = False):
    catalog = _catalog(request)
    packs = []
    for manifest in catalog.list_manifests():
        packs.append(
            {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "path": manifest.path,
                "origin": manifest.origin,
            }
        )
    if include_archived:
        packs.extend(list_archived_packs(catalog))
    return {"packs": packs}


@router.get("/api/skills/archived-packs")
async def get_archived_packs(request: Request):
    catalog = _catalog(request)
    return {"packs": list_archived_packs(catalog)}


@router.post("/api/skills/user-packs/{pack_id:path}/archive")
async def post_archive_user_pack(request: Request, pack_id: str, payload: Optional[UserPackArchive] = None):
    catalog = _catalog(request)
    confirm = bool(payload.confirm) if payload is not None else False
    try:
        result = archive_pack(catalog, pack_id, confirm=confirm)
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if not result.get("success"):
        code = 409 if "already exists" in str(result.get("error") or "") else 400
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to archive pack"))
    return result


@router.post("/api/skills/user-packs/{pack_id:path}/unarchive")
async def post_unarchive_user_pack(request: Request, pack_id: str):
    catalog = _catalog(request)
    try:
        result = unarchive_pack(catalog, pack_id)
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if result.get("not_found"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Archived pack '{pack_id}' not found"))
    if not result.get("success"):
        code = 409 if result.get("conflict") else 400
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to unarchive pack"))
    return result


@router.post("/api/skills/user-packs")
async def create_user_pack(request: Request, payload: UserPackCreate):
    catalog = _catalog(request)
    try:
        result = catalog.create_pack(payload.id, name=payload.name, description=payload.description)
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if result.get("conflict"):
        raise HTTPException(status_code=409, detail=result["error"])
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create pack"))
    return result


@router.get("/api/skills/user-packs/{pack_id:path}")
async def get_user_pack(request: Request, pack_id: str):
    catalog = _catalog(request)
    try:
        result = catalog.read_pack(pack_id)
        if result.get("not_found"):
            archived = read_archived_pack(catalog, pack_id)
            if archived.get("success"):
                result = archived
            else:
                raise HTTPException(status_code=404, detail=f"Pack '{pack_id}' not found.")
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if result.get("not_found") or not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Pack '{pack_id}' not found."))
    return result


@router.delete("/api/skills/user-packs/{pack_id:path}")
async def delete_user_pack(
    request: Request,
    pack_id: str,
    confirm: bool = False,
    confirm_seed: bool = False,
    payload: Optional[UserPackDelete] = None,
):
    catalog = _catalog(request)
    if payload is not None:
        confirm = confirm or bool(payload.confirm)
        confirm_seed = confirm_seed or bool(payload.confirm_seed)
    try:
        result = delete_pack(catalog, pack_id, confirm=confirm, confirm_seed=confirm_seed)
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if result.get("confirm_required"):
        raise HTTPException(status_code=400, detail=result.get("error", "confirm=true is required"))
    if result.get("confirm_seed_required") or result.get("bundled") and not result.get("success"):
        raise HTTPException(
            status_code=409,
            detail=result.get("error", "bundled seed, archive instead or pass confirm_seed"),
        )
    if result.get("jail"):
        raise _http_jail(PackJailError(result.get("error") or "Path traversal rejected."))
    if result.get("not_found"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Pack '{pack_id}' not found"))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to delete pack"))
    from pathlib import Path

    from src.application.skills.workshop import clear_operator_skill_side_effects

    paths = getattr(request.app.state, "data_dir_paths", None)
    data_root = getattr(paths, "root", None) if paths is not None else None
    store = getattr(request.app.state, "store", None)
    db_path = getattr(store, "db_path", None) if store is not None else None
    if data_root is not None:
        clear_operator_skill_side_effects(
            Path(data_root),
            pack_id,
            db_path=str(db_path) if db_path else None,
        )
    return result


@router.put("/api/skills/user-packs/{pack_id:path}")
async def put_user_pack(request: Request, pack_id: str, payload: UserPackWrite):
    catalog = _catalog(request)
    try:
        result = catalog.save_pack(
            pack_id,
            name=payload.name,
            description=payload.description,
            instructions=payload.instructions,
        )
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if not result.get("success"):
        code = 404 if result.get("not_found") else 400
        raise HTTPException(status_code=code, detail=result.get("error", "Failed to save pack"))
    return result


class SkillLintRequest(BaseModel):
    text: Optional[str] = None
    content: Optional[str] = None
    path: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None


@router.post("/api/skills/lint")
async def lint_skill_content(payload: SkillLintRequest):
    """Mechanically lint draft SKILL.md content against ADR-0054 capability contracts [REQ-390-001]."""
    from src.application.skills.linter import CapabilityLinter, SkillContractCompiler
    from src.domain.skills.contract import LintSeverity

    raw_text = payload.text if payload.text is not None else payload.content
    if raw_text is None and not payload.path and not (payload.name or payload.description or payload.instructions):
        raise HTTPException(status_code=400, detail="Either 'content' or 'path' must be provided.")

    if payload.path and raw_text is None and not (payload.name or payload.instructions):
        linter = CapabilityLinter()
        contract, violations = linter.lint_file(payload.path)
    else:
        compiler = SkillContractCompiler()
        if raw_text is None:
            name = (payload.name or "").strip()
            desc = (payload.description or "").strip()
            body = (payload.instructions or "").strip()
            raw_text = f"---\nname: {name}\ndescription: {desc}\n---\n\n{body}\n"
        contract, violations = compiler.compile(raw_text, path=payload.path)

    errors = [v for v in violations if v.severity == LintSeverity.ERROR or v.severity.value == "error"]
    warnings = [v for v in violations if v.severity == LintSeverity.WARNING or v.severity.value == "warning"]

    contract_dict = contract.model_dump(mode="json") if contract else None
    if contract_dict:
        contract_dict["tools_count"] = len(contract.requires_tools)

    return {
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "violations": [
            {
                "rule_id": v.rule_id,
                "rule": v.rule_id,
                "rule_name": v.rule_name,
                "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity),
                "message": v.message,
                "line_number": v.line_number,
            }
            for v in violations
        ],
        "contract": contract_dict,
    }


class DistillSkillRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message_id: str = Field(..., min_length=1)
    guidance: Optional[str] = None


class AdoptSkillRequest(BaseModel):
    target_agent_id: str = Field(..., min_length=1)
    skill_id: str = Field(..., min_length=1)
    runbook_markdown: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    message_id: Optional[str] = None


@router.post("/api/skills/distill")
async def post_distill_skill(request: Request, payload: DistillSkillRequest):
    """[REQ-SKIL-010, REQ-SKIL-015] Analyze recent conversation turn and synthesize a persistent SKILL.md proposal."""
    from src.application.skills.distillation_service import DistillTurnNotFound, SkillDistillationService

    store = request.app.state.store
    session = store.get_session(payload.session_id) if hasattr(store, "get_session") else None
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{payload.session_id}' not found.")

    gateway = getattr(request.app.state, "gateway", None)
    paths = getattr(request.app.state, "data_dir_paths", None)
    data_dir = paths.root if paths else None
    registry = getattr(request.app.state, "registry", None)

    service = SkillDistillationService(
        store=store,
        gateway=gateway,
        data_dir=data_dir,
        agent_registry=registry,
    )
    try:
        result = await service.distill_turn(
            session_id=payload.session_id,
            message_id=payload.message_id,
            guidance=payload.guidance,
        )
    except DistillTurnNotFound as exc:  # CARD-500 REQ-500-003: plain reason, no fallback
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result


@router.post("/api/skills/adopt")
async def post_adopt_skill(request: Request, payload: AdoptSkillRequest):
    """[REQ-SKIL-013, REQ-SKIL-016] Adopt a distilled SKILL.md and update proposal status in session history."""
    from src.application.skills.distillation_service import (
        AdoptAgentNotFound,
        AdoptSkillConflict,
        SkillDistillationService,
    )

    store = request.app.state.store
    paths = getattr(request.app.state, "data_dir_paths", None)
    data_dir = paths.root if paths else None
    if data_dir is None:
        raise HTTPException(status_code=500, detail="Data directory not configured.")

    registry = getattr(request.app.state, "registry", None)
    service = SkillDistillationService(
        store=store,
        data_dir=data_dir,
        agent_registry=registry,
    )
    try:
        result = service.adopt_skill(
            target_agent_id=payload.target_agent_id,
            skill_id=payload.skill_id,
            runbook_markdown=payload.runbook_markdown,
            data_dir=data_dir,
        )

        # Update persisted chat message proposal status [CARD-358, REQ-SKIL-016]
        if payload.message_id and hasattr(store, "update_message"):
            now_iso = datetime.now(timezone.utc).isoformat()
            existing_msg = store.get_message(payload.message_id) if hasattr(store, "get_message") else None
            cdata = {}
            if existing_msg and existing_msg.content:
                try:
                    cdata = json.loads(existing_msg.content)
                except Exception:
                    cdata = {}
            cdata["adoption_state"] = "adopted"
            cdata["adopted_at"] = now_iso
            cdata["skill_id"] = payload.skill_id
            cdata["target_agent_id"] = payload.target_agent_id
            store.update_message(payload.message_id, json.dumps(cdata))

        return result
    except AdoptSkillConflict as exc:  # CARD-502 REQ-502-008
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdoptAgentNotFound as exc:  # CARD-502 REQ-502-007
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to adopt skill: {exc}") from exc
