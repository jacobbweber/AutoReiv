"""User skill pack studio API [REQ-DATA-012 - REQ-DATA-014]. Writes jailed to $DATA_DIR/skills."""

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
            result = read_archived_pack(catalog, pack_id)
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if result.get("not_found") or not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Pack '{pack_id}' not found"))
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
