"""Data directory, backups, reply limits, allowed origins, and live approval mode routes [CARD-701]."""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.infrastructure.data.backup import DataDirBackupService, DataDirRestoreError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])


def _data_dir_paths(request: Request):
    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        raise HTTPException(status_code=500, detail="Data directory is not resolved")
    return paths


@router.get("/api/data-dir")
async def get_data_dir(request: Request):
    """Resolved user data directory paths [REQ-DATA-001, REQ-DATA-002]."""
    from src.infrastructure.data.wiki_gate import (
        configured_wiki_path,
        inspect_wiki_path,
        resolve_deploy_mode,
    )

    paths = getattr(request.app.state, "data_dir_paths", None)
    if paths is None:
        return {"root": "", "db_path": "", "wiki_path": "", "skills_path": ""}
    mode = resolve_deploy_mode()
    explicit = configured_wiki_path()
    structural = paths.wiki_path
    if explicit is not None:
        display = explicit
    elif mode == "local":
        display = structural
    else:
        display = None
    status = inspect_wiki_path(display, deploy_mode=mode)
    return {
        "root": str(paths.root),
        "db_path": str(paths.db_path),
        "wiki_path": str(display) if display else "",
        "wiki_structural_path": str(structural),
        "skills_path": str(paths.skills_path),
        "wiki_status": status.status,
        "wiki_message": status.message,
        "wiki_exists": status.exists,
        "deploy_mode": status.deploy_mode,
    }


class WikiPathBody(BaseModel):
    path: str
    confirm_scaffold: bool = True


@router.put("/api/settings/wiki-path")
async def put_wiki_path(request: Request, body: WikiPathBody):
    """Persist wiki folder path; optionally scaffold standard layout [ADR-0056 local default]."""
    from src.domain.wiki.store import WikiStore
    from src.infrastructure.data.resolver import WIKI_PATH_SETTING_KEY, WIKI_SCAFFOLD_CONFIRMED_KEY
    from src.infrastructure.data.wiki_gate import inspect_wiki_path, resolve_deploy_mode

    raw = (body.path or "").strip()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Wiki folder path is required. Default is a wiki folder under your data directory.",
        )
    path = Path(raw).expanduser()
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Store unavailable")
    from src.application.wiki.service import WikiService

    store.set_setting(WIKI_PATH_SETTING_KEY, str(path))
    os.environ["AUTOREIV_WIKI_PATH"] = str(path)
    request.app.state.wiki_path = str(path)
    scaffolded = False
    if body.confirm_scaffold:
        path.mkdir(parents=True, exist_ok=True)
        store.set_setting(WIKI_SCAFFOLD_CONFIRMED_KEY, True)
        try:
            WikiStore(root_dir=path, auto_seed=False).scaffold(seed_starter=False, auto_migrate=False)
            scaffolded = True
        except Exception as exc:
            logger.warning("Wiki scaffold soft-failed: %s", exc)
            scaffolded = True
    request.app.state.wiki_service = WikiService(wiki_root=str(path))
    status = inspect_wiki_path(path, deploy_mode=resolve_deploy_mode())
    return {
        "status": "updated",
        "wiki_path": str(path),
        "wiki_status": status.status,
        "wiki_message": status.message,
        "scaffolded": scaffolded,
    }


@router.get("/api/settings/wiki-path")
async def get_wiki_path(request: Request):
    """Wiki path status for Settings UI (local defaults to data_root/wiki when unset)."""
    from src.infrastructure.data.wiki_gate import configured_wiki_path, inspect_wiki_path, resolve_deploy_mode

    mode = resolve_deploy_mode()
    path = configured_wiki_path()
    if path is None and mode == "local":
        paths = getattr(request.app.state, "data_dir_paths", None)
        if paths is not None:
            path = paths.wiki_path
    status = inspect_wiki_path(path, deploy_mode=mode)
    return {
        "wiki_path": str(path) if path else "",
        "wiki_status": status.status,
        "wiki_message": status.message,
        "wiki_exists": status.exists,
        "deploy_mode": status.deploy_mode,
    }


@router.post("/api/data-dir/backup")
async def backup_data_dir(request: Request):
    """Zip the resolved data dir and return it as a download [REQ-DATA-007]."""
    paths = _data_dir_paths(request)
    dest = DataDirBackupService(paths).backup()
    return FileResponse(
        path=str(dest),
        media_type="application/zip",
        filename=dest.name,
        headers={"X-Backup-Path": str(dest)},
    )


@router.post("/api/data-dir/restore")
async def restore_data_dir(
    request: Request,
    archive: UploadFile = File(...),
    confirm: bool = Form(False),
):
    """Replace the data dir from a zip. Requires confirm=true [REQ-DATA-008]."""
    paths = _data_dir_paths(request)
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Restore requires confirm=true; live tree unchanged",
        )
    suffix = Path(archive.filename or "restore.zip").suffix or ".zip"
    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "wb") as handle:
            while True:
                chunk = await archive.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        DataDirBackupService(paths).restore(tmp_path, confirm=True)
    except DataDirRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
    return {"status": "restored", "root": str(paths.root)}


@router.get("/api/data-dir/backups")
async def list_data_dir_backups(request: Request):
    """List existing backup archives, catalog config, and destination path [CARD-404]."""
    paths = _data_dir_paths(request)
    store = getattr(request.app.state, "store", None)
    service = DataDirBackupService(paths)
    bdir = paths.backups_path
    backups = service.list_backups(bdir)
    config = {
        "schedule": store.get_setting("backup_schedule", "disabled") if store else "disabled",
        "retention_count": store.get_setting("backup_retention", 7) if store else 7,
        "backup_dir": str(bdir),
        "last_backup_time": store.get_setting("last_backup_time", None) if store else None,
    }
    return {
        "status": "ok",
        "backup_dir": str(bdir),
        "config": config,
        "backups": backups,
    }


@router.post("/api/data-dir/backups/run")
async def run_data_dir_backup(request: Request):
    """Trigger an immediate backup and apply the retention pruning policy [CARD-404]."""
    paths = _data_dir_paths(request)
    store = getattr(request.app.state, "store", None)
    service = DataDirBackupService(paths)
    bdir = paths.backups_path
    dest = service.backup(backup_dir=bdir)
    retention = 7
    if store and hasattr(store, "get_setting"):
        retention = int(store.get_setting("backup_retention", 7))
    pruned = service.prune_backups(retention_count=retention, backup_dir=bdir)
    now_iso = datetime.now(timezone.utc).isoformat()
    if store and hasattr(store, "set_setting"):
        store.set_setting("last_backup_time", now_iso)
    return {
        "status": "created",
        "filename": dest.name,
        "path": str(dest.resolve()),
        "size_bytes": dest.stat().st_size,
        "size_mb": round(dest.stat().st_size / (1024 * 1024), 2),
        "pruned": pruned,
        "created_at": now_iso,
    }


@router.get("/api/data-dir/backups/{filename}/download")
async def download_backup_archive(filename: str, request: Request):
    """Download a specific backup archive by filename [CARD-404]."""
    paths = _data_dir_paths(request)
    clean_name = str(filename).strip()
    if not clean_name or ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        raise HTTPException(status_code=400, detail="Invalid backup filename")
    bdir = paths.backups_path.resolve()
    target = (bdir / clean_name).resolve()
    if target.parent != bdir or not target.is_file():
        raise HTTPException(status_code=404, detail="Backup archive not found")
    return FileResponse(
        path=str(target),
        media_type="application/zip",
        filename=clean_name,
        headers={"X-Backup-Path": str(target)},
    )


@router.delete("/api/data-dir/backups/{filename}")
async def delete_backup_archive(filename: str, request: Request):
    """Delete a specific backup archive by filename [CARD-404]."""
    paths = _data_dir_paths(request)
    service = DataDirBackupService(paths)
    try:
        deleted = service.delete_backup(filename, backup_dir=paths.backups_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Backup archive not found")
    return {"status": "deleted", "filename": filename}


@router.post("/api/data-dir/backups/{filename}/restore")
async def restore_from_catalog(filename: str, request: Request):
    """Restore the data directory from an existing server-side backup [CARD-404]."""
    paths = _data_dir_paths(request)
    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        pass
    confirm = body.get("confirm", False)
    if not confirm:
        raise HTTPException(status_code=400, detail="Restore requires confirm=true; live tree unchanged")
    clean_name = str(filename).strip()
    if not clean_name or ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        raise HTTPException(status_code=400, detail="Invalid backup filename")
    bdir = paths.backups_path.resolve()
    target = (bdir / clean_name).resolve()
    if target.parent != bdir or not target.is_file():
        raise HTTPException(status_code=404, detail="Backup archive not found")
    service = DataDirBackupService(paths)
    try:
        service.restore(target, confirm=True)
    except DataDirRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "restored", "filename": clean_name, "root": str(paths.root)}


@router.get("/api/data-dir/backup-config")
async def get_backup_config(request: Request):
    """Get the current automated backup configuration [CARD-404]."""
    paths = _data_dir_paths(request)
    store = getattr(request.app.state, "store", None)
    return {
        "schedule": store.get_setting("backup_schedule", "disabled") if store else "disabled",
        "retention_count": store.get_setting("backup_retention", 7) if store else 7,
        "backup_dir": str(paths.backups_path),
        "last_backup_time": store.get_setting("last_backup_time", None) if store else None,
    }


@router.put("/api/data-dir/backup-config")
async def update_backup_config(request: Request):
    """Update automated backup schedule, retention count, and backup directory [CARD-404]."""
    paths = _data_dir_paths(request)
    store = getattr(request.app.state, "store", None)
    body = await request.json()
    schedule = body.get("schedule")
    retention = body.get("retention_count")
    backup_dir = body.get("backup_dir")

    from src.infrastructure.data.migrate import persist_autoreiv_backup_config
    from src.infrastructure.data.resolver import repo_root

    try:
        persisted = persist_autoreiv_backup_config(
            backup_dir=backup_dir,
            schedule=schedule,
            retention=retention,
            checkout=getattr(request.app.state, "checkout_root", None) or repo_root(),
            store=store,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if backup_dir is not None:
        clean_bdir = str(backup_dir).strip()
        new_backup_path = Path(clean_bdir).expanduser().resolve() if clean_bdir else paths.root / "backups"
        object.__setattr__(paths, "backups_path", new_backup_path)
        new_backup_path.mkdir(parents=True, exist_ok=True)

    return {
        "status": "updated",
        "config": {
            "schedule": store.get_setting("backup_schedule", "disabled") if store else "disabled",
            "retention_count": store.get_setting("backup_retention", 7) if store else 7,
            "backup_dir": str(paths.backups_path),
            "last_backup_time": store.get_setting("last_backup_time", None) if store else None,
        },
        "persisted_via": persisted,
    }


@router.get("/api/settings/reply-limits")
async def get_reply_limits(request: Request):
    """CARD-567: per-reply limits for every streaming model call (tokens and wall-clock seconds).
    CARD-592: plus provider_idle_seconds, phase_seconds and helper_seconds (model-call waits)."""
    from src.application.kernel.reply_limits import SETTING_KEY, resolve_all_limits

    return {"key": SETTING_KEY, **resolve_all_limits(request.app.state.store)}


@router.put("/api/settings/reply-limits")
async def put_reply_limits(request: Request):
    """CARD-567/592: save any Reply limits field (positive integers; null or 0 clears back to env/default).
    CARD-605: wiki_lookups_per_reply must be 1-50."""
    from src.application.kernel.reply_limits import (
        SETTING_KEY,
        TIMEOUT_FIELDS,
        WIKI_LOOKUPS_FIELD,
        WIKI_LOOKUPS_MAX,
        WIKI_LOOKUPS_MIN,
        resolve_all_limits,
    )

    body = await request.json()
    store = request.app.state.store
    saved = dict(store.get_setting(SETTING_KEY) or {})
    for field in ("max_tokens", "max_seconds", *TIMEOUT_FIELDS, WIKI_LOOKUPS_FIELD):
        if field not in body:
            continue
        value = body.get(field)
        try:
            n = int(value) if value is not None else 0
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"{field} must be a positive integer") from None
        if n < 0:
            raise HTTPException(status_code=400, detail=f"{field} must be a positive integer")
        if n and field == WIKI_LOOKUPS_FIELD and not WIKI_LOOKUPS_MIN <= n <= WIKI_LOOKUPS_MAX:
            raise HTTPException(
                status_code=400, detail=f"{field} must be between {WIKI_LOOKUPS_MIN} and {WIKI_LOOKUPS_MAX}"
            )
        if n:
            saved[field] = n
        else:
            saved.pop(field, None)
    store.set_setting(SETTING_KEY, saved)
    return {"key": SETTING_KEY, **resolve_all_limits(store)}


@router.get("/api/settings/allowed-origins")
async def get_allowed_origins(request: Request):
    """CARD-602: extra browser origins allowed to call owner routes (phone reverse proxy, etc.)."""
    from src.web.origin_guard import SETTING_KEY, parse_extra_origins

    store = request.app.state.store
    try:
        origins = parse_extra_origins(store.get_setting(SETTING_KEY) or [])
    except ValueError:
        origins = []
    return {"key": SETTING_KEY, "origins": origins}


@router.put("/api/settings/allowed-origins")
async def put_allowed_origins(request: Request):
    """CARD-602: replace the extra-origins list. Empty strings are dropped; bad URLs return 400."""
    from src.web.origin_guard import SETTING_KEY, parse_extra_origins

    body = await request.json()
    raw = body.get("origins", [])
    if raw is not None and not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="origins must be a list of http(s) URLs")
    try:
        origins = parse_extra_origins(raw or [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    request.app.state.store.set_setting(SETTING_KEY, origins)
    return {"key": SETTING_KEY, "origins": origins}


@router.get("/api/settings/approval-mode")
async def get_approval_mode(request: Request):
    """CARD-701: resolve live ApprovalMode (`strict`, `balanced`, `hands_off`) and source (`setting`, `env`, `default`)."""
    from src.application.safety.approval_mode import resolve_approval_mode_info

    store = getattr(request.app.state, "store", None)
    return resolve_approval_mode_info(store)


@router.put("/api/settings/approval-mode")
async def put_approval_mode(request: Request):
    """CARD-701: save live ApprovalMode (`strict`, `balanced`, `hands_off`; empty string clears back to env/default)."""
    from src.application.safety.approval_mode import save_approval_mode

    body = await request.json()
    raw_mode = body.get("approval_mode", body.get("mode"))
    store = getattr(request.app.state, "store", None)
    try:
        return save_approval_mode(store, raw_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
