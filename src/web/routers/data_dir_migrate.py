"""CARD-313 data-dir migrate API route."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.infrastructure.data.migrate import (
    DataDirRelocateError,
    migrate_data_dir,
    resolve_paths_for_root,
)
from src.web.routers.settings import _data_dir_paths

router = APIRouter(tags=["Settings"])


class DataDirMigrateRequest(BaseModel):
    destination: str


@router.post("/api/data-dir/migrate")
async def migrate_data_dir_api(request: Request, body: DataDirMigrateRequest):
    """Copy live data root to destination, backup-rename source, persist AUTOREIV_DATA_DIR [CARD-313]."""
    paths = _data_dir_paths(request)
    try:
        result = migrate_data_dir(paths.root, body.destination)
    except DataDirRelocateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    new_paths = resolve_paths_for_root(result.destination)
    request.app.state.data_dir_paths = new_paths
    request.app.state.wiki_path = str(new_paths.wiki_path)
    if hasattr(request.app.state, "data_dir"):
        request.app.state.data_dir = str(new_paths.root)
    settings = getattr(request.app.state, "settings", None)
    if settings is not None and hasattr(settings, "data_dir"):
        try:
            settings.data_dir = str(new_paths.root)
        except Exception:
            pass

    return {
        "status": "migrated",
        "source": str(result.source),
        "root": str(result.destination),
        "backup_path": str(result.backup_path) if result.backup_path else None,
        "persisted_via": result.persisted_via,
        "db_path": str(new_paths.db_path),
        "wiki_path": str(new_paths.wiki_path),
        "skills_path": str(new_paths.skills_path),
    }
