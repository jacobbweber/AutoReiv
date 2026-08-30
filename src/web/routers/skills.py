"""User skill pack studio API [REQ-DATA-012 - REQ-DATA-014]. Writes jailed to $DATA_DIR/skills."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

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
async def list_user_packs(request: Request):
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
    return {"packs": packs}


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
    except PackJailError as exc:
        raise _http_jail(exc) from exc
    if result.get("not_found") or not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", f"Pack '{pack_id}' not found"))
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
