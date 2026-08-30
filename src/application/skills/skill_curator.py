"""Skill curator: unused user packs go active -> stale -> archive.

[REQ-IMPROVE-013] [REQ-IMPROVE-014] [REQ-IMPROVE-015] [REQ-IMPROVE-016]

Unused user packs: active --(30d)--> stale --(90d)--> archive (move).
Never deletes SKILL.md. Never auto-archives bundled seeds (okta-admin /
BUNDLED_PACK_IDS). Never touches repo src/infrastructure/skills/seeds/.
Unknown last-used fails closed. Auto-archive is opt-in (paused routine /
skill-eval-sleep metadata.auto_archive).
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.skills.user_catalog import (
    ARCHIVE_DIRNAME,
    SKILL_MD_NAME,
    SKIP_LIST_DIRNAMES,
    PackJailError,
    UserSkillCatalog,
)
from src.infrastructure.skills.seed import BUNDLED_PACK_IDS, bundled_seed_root

logger = logging.getLogger(__name__)

ROUTINE_ID = "skill-curator"
AGENT_ID = "agent-builder"
SOURCE = "skill-curator"
STALE_AFTER_DAYS = 30
ARCHIVE_AFTER_DAYS = 90
LAST_USED_NAME = ".last_used"

STATUS_ACTIVE = "active"
STATUS_STALE = "stale"
STATUS_ARCHIVE = "archive"
STATUS_BUNDLED = "bundled"
STATUS_UNKNOWN = "unknown"
STATUS_SKIPPED = "skipped"


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_iso(text: str) -> Optional[datetime]:
    raw = (text or "").strip()
    if not raw or raw.lower() in {"unknown", "none", "null"}:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return _aware(parsed)


def is_bundled_pack(pack_id: str) -> bool:
    return pack_id in BUNDLED_PACK_IDS


def repo_seed_root() -> Path:
    return bundled_seed_root()


def last_used_at(
    pack_dir: Union[str, Path],
    *,
    pack_id: Optional[str] = None,
    overrides: Optional[Dict[str, Optional[datetime]]] = None,
) -> Optional[datetime]:
    """Return last-used instant, or None when unknown (fail closed).

    last-used is max(SKILL.md mtime, .last_used sidecar, override). An explicit
    override of None means unknown even if mtime exists.
    """
    pid = pack_id or Path(pack_dir).name
    if overrides is not None and pid in overrides:
        return _aware(overrides[pid])
    candidates: List[datetime] = []
    root = Path(pack_dir)
    skill = root / SKILL_MD_NAME
    if skill.is_file():
        try:
            candidates.append(datetime.fromtimestamp(skill.stat().st_mtime, tz=timezone.utc))
        except OSError:
            pass
    sidecar = root / LAST_USED_NAME
    if sidecar.is_file():
        try:
            parsed = _parse_iso(sidecar.read_text(encoding="utf-8"))
        except OSError:
            parsed = None
        if parsed is not None:
            candidates.append(parsed)
    if not candidates:
        return None
    return max(candidates)


def classify_age(
    last_used: Optional[datetime],
    *,
    now: Optional[datetime] = None,
    stale_days: int = STALE_AFTER_DAYS,
    archive_days: int = ARCHIVE_AFTER_DAYS,
) -> str:
    if last_used is None:
        return STATUS_UNKNOWN
    now_utc = _aware(now) or datetime.now(timezone.utc)
    used = _aware(last_used)
    if used is None:
        return STATUS_UNKNOWN
    age = now_utc - used
    if age >= timedelta(days=int(archive_days)):
        return STATUS_ARCHIVE
    if age >= timedelta(days=int(stale_days)):
        return STATUS_STALE
    return STATUS_ACTIVE


def _catalog_root(catalog: UserSkillCatalog) -> Path:
    if catalog.skills_dir is None:
        raise PackJailError("Skills directory is not configured.")
    return catalog.skills_dir.expanduser().resolve()


def archive_pack_dir(catalog: UserSkillCatalog, pack_id: str) -> Path:
    """Jailed $DATA_DIR/skills/_archive/<id>/."""
    catalog.pack_dir(pack_id)
    root = _catalog_root(catalog)
    dest = (catalog.skills_dir / ARCHIVE_DIRNAME / pack_id).resolve()
    try:
        dest.relative_to(root / ARCHIVE_DIRNAME)
    except ValueError as exc:
        raise PackJailError("Path traversal rejected.") from exc
    return dest


def record_pack_use(catalog: UserSkillCatalog, pack_id: str) -> None:
    """Write .last_used sidecar so last-used is known after skill_view/save."""
    try:
        root = catalog.pack_dir(pack_id)
        if not root.is_dir():
            return
        (root / LAST_USED_NAME).write_text(
            datetime.now(timezone.utc).isoformat(),
            encoding="utf-8",
        )
    except (OSError, PackJailError) as exc:
        logger.debug("record_pack_use skipped for %s: %s", pack_id, exc)


def archive_pack(
    catalog: UserSkillCatalog,
    pack_id: str,
    *,
    confirm: bool = False,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Move a live pack to $DATA_DIR/skills/_archive/<id>/. Never delete SKILL.md."""
    del now
    if is_bundled_pack(pack_id) and not confirm:
        return {
            "success": False,
            "archived": False,
            "pack_id": pack_id,
            "error": (
                f"Bundled seed '{pack_id}' is not auto-archived. "
                "Explicit confirm is required to archive a bundled pack."
            ),
            "bundled": True,
            "skill_md_deleted": False,
        }
    try:
        live = catalog.pack_dir(pack_id)
        dest = archive_pack_dir(catalog, pack_id)
    except PackJailError as exc:
        return {
            "success": False,
            "archived": False,
            "pack_id": pack_id,
            "error": str(exc),
            "skill_md_deleted": False,
        }
    if not live.is_dir():
        return {
            "success": False,
            "archived": False,
            "pack_id": pack_id,
            "error": f"Pack '{pack_id}' is not a live directory.",
            "skill_md_deleted": False,
        }
    if dest.exists():
        return {
            "success": False,
            "archived": False,
            "pack_id": pack_id,
            "error": f"Archive dest already exists for '{pack_id}'; fail closed.",
            "skill_md_deleted": False,
        }
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(live), str(dest))
    dest_skill = dest / SKILL_MD_NAME
    return {
        "success": True,
        "archived": True,
        "pack_id": pack_id,
        "from": str(live),
        "to": str(dest),
        "skill_md": str(dest_skill) if dest_skill.is_file() else None,
        "skill_md_deleted": False,
        "bundled": is_bundled_pack(pack_id),
    }


def unarchive_pack(catalog: UserSkillCatalog, pack_id: str) -> Dict[str, Any]:
    """Move $DATA_DIR/skills/_archive/<id>/ back to $DATA_DIR/skills/<id>/. Dest-exists fails closed."""
    try:
        live = catalog.pack_dir(pack_id)
        src = archive_pack_dir(catalog, pack_id)
    except PackJailError as exc:
        return {
            "success": False,
            "unarchived": False,
            "pack_id": pack_id,
            "error": str(exc),
        }
    if not src.is_dir():
        return {
            "success": False,
            "unarchived": False,
            "pack_id": pack_id,
            "error": f"Archived pack '{pack_id}' not found.",
            "not_found": True,
        }
    if live.exists():
        return {
            "success": False,
            "unarchived": False,
            "pack_id": pack_id,
            "error": f"Live dest already exists for '{pack_id}'; fail closed.",
            "conflict": True,
        }
    live.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(live))
    if hasattr(catalog, "list_manifests"):
        catalog.list_manifests()
    return {
        "success": True,
        "unarchived": True,
        "pack_id": pack_id,
        "from": str(src),
        "to": str(live),
        "proposal_id": None,
        "committed": False,
    }


def list_archived_packs(catalog: UserSkillCatalog) -> List[Dict[str, Any]]:
    if catalog.skills_dir is None:
        return []
    root = catalog.skills_dir / ARCHIVE_DIRNAME
    if not root.is_dir():
        return []
    from src.application.skills.dynamic_loader import DynamicSkillLoader

    packs: List[Dict[str, Any]] = []
    for manifest in DynamicSkillLoader.list_skill_manifests(str(root)):
        packs.append(
            {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "path": manifest.path,
                "origin": "archived",
            }
        )
    return packs


def read_archived_pack(catalog: UserSkillCatalog, pack_id: str) -> Dict[str, Any]:
    """Read SKILL.md from $DATA_DIR/skills/_archive/<id>/ for Studio view."""
    from src.application.skills.dynamic_loader import DynamicSkillLoader

    try:
        dest = archive_pack_dir(catalog, pack_id)
    except PackJailError as exc:
        return {"success": False, "error": str(exc), "pack_id": pack_id}
    skill = dest / SKILL_MD_NAME
    if not skill.is_file():
        return {
            "success": False,
            "error": f"Archived pack '{pack_id}' not found.",
            "not_found": True,
            "pack_id": pack_id,
        }
    parsed = DynamicSkillLoader.load_skill_from_markdown(str(skill))
    if not parsed:
        return {"success": False, "error": f"Failed to load archived SKILL.md for pack '{pack_id}'."}
    tools_meta = []
    for tool in parsed.get("tools") or []:
        tools_meta.append({"name": tool.name, "description": tool.description})
    return {
        "success": True,
        "archived": True,
        "manifest": {
            "id": pack_id,
            "name": parsed.get("name", pack_id),
            "description": parsed.get("description", ""),
            "path": str(skill),
            "origin": "archived",
        },
        "instructions": parsed.get("instructions", ""),
        "tools": tools_meta,
    }


def _assert_deletable_under_skills(target: Path, root: Path) -> Path:
    resolved = target.expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PackJailError("Path traversal rejected.") from exc
    if resolved == root:
        raise PackJailError("Refusing to delete the skills root.")
    archive_root = (root / ARCHIVE_DIRNAME).resolve()
    if resolved == archive_root:
        raise PackJailError("Refusing to delete the archive root.")
    return resolved


def delete_pack(
    catalog: UserSkillCatalog,
    pack_id: str,
    *,
    confirm: bool = False,
    confirm_seed: bool = False,
) -> Dict[str, Any]:
    """Hard-delete a jailed user pack (live and/or _archive). Never repo seeds."""
    if not confirm:
        return {
            "success": False,
            "deleted": False,
            "pack_id": pack_id,
            "error": "confirm=true is required to hard-delete a user pack.",
            "confirm_required": True,
        }
    if is_bundled_pack(pack_id) and not confirm_seed:
        return {
            "success": False,
            "deleted": False,
            "pack_id": pack_id,
            "error": "bundled seed, archive instead or pass confirm_seed",
            "bundled": True,
            "confirm_seed_required": True,
        }
    try:
        live = catalog.pack_dir(pack_id)
        archived = archive_pack_dir(catalog, pack_id)
        root = _catalog_root(catalog)
    except PackJailError as exc:
        return {
            "success": False,
            "deleted": False,
            "pack_id": pack_id,
            "error": str(exc),
            "jail": True,
        }

    seed_root = repo_seed_root()
    seed_resolved = seed_root.expanduser().resolve() if seed_root.exists() else None
    seed_before: Dict[str, float] = {}
    if seed_root.is_dir():
        for path in seed_root.rglob(SKILL_MD_NAME):
            try:
                seed_before[str(path)] = path.stat().st_mtime
            except OSError:
                continue

    removed: List[str] = []
    try:
        for target in (live, archived):
            if not target.exists():
                continue
            resolved = _assert_deletable_under_skills(target, root)
            if seed_resolved is not None:
                try:
                    resolved.relative_to(seed_resolved)
                except ValueError:
                    pass
                else:
                    return {
                        "success": False,
                        "deleted": False,
                        "pack_id": pack_id,
                        "error": "Refusing to delete repository seed sources.",
                        "repo_seeds_untouched": True,
                    }
            if resolved.is_dir():
                shutil.rmtree(resolved)
                removed.append(str(resolved))
            elif resolved.is_file():
                resolved.unlink()
                removed.append(str(resolved))
    except PackJailError as exc:
        return {
            "success": False,
            "deleted": False,
            "pack_id": pack_id,
            "error": str(exc),
            "jail": True,
        }

    seed_after_ok = True
    seed_touched: List[str] = []
    for path_text, mtime in seed_before.items():
        path = Path(path_text)
        if not path.is_file():
            seed_after_ok = False
            seed_touched.append(path_text)
            continue
        try:
            if path.stat().st_mtime != mtime:
                seed_after_ok = False
                seed_touched.append(path_text)
        except OSError:
            seed_after_ok = False
            seed_touched.append(path_text)

    if not removed:
        return {
            "success": False,
            "deleted": False,
            "pack_id": pack_id,
            "error": f"Pack '{pack_id}' not found.",
            "not_found": True,
            "repo_seeds_untouched": seed_after_ok,
        }
    if hasattr(catalog, "list_manifests"):
        catalog.list_manifests()
    return {
        "success": True,
        "deleted": True,
        "pack_id": pack_id,
        "removed": removed,
        "bundled": is_bundled_pack(pack_id),
        "repo_seeds_untouched": seed_after_ok,
        "repo_seeds_touched": seed_touched,
    }


def _iter_live_pack_dirs(catalog: UserSkillCatalog) -> List[Path]:
    if catalog.skills_dir is None or not catalog.skills_dir.is_dir():
        return []
    found: List[Path] = []
    for child in sorted(catalog.skills_dir.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SKIP_LIST_DIRNAMES:
            continue
        if (child / SKILL_MD_NAME).is_file():
            found.append(child)
    return found


def curate_user_skill_packs(
    catalog: UserSkillCatalog,
    *,
    now: Optional[datetime] = None,
    auto_archive: bool = False,
    last_used_by_id: Optional[Dict[str, Optional[datetime]]] = None,
    stale_days: int = STALE_AFTER_DAYS,
    archive_days: int = ARCHIVE_AFTER_DAYS,
    confirm_bundled: bool = False,
) -> Dict[str, Any]:
    """Classify live packs. Move only unused user packs past the archive window.

    auto_archive defaults False so nightly/harvest is not destructive.
    Bundled seeds are never auto-archived. Unknown last-used is not archived.
    Repo seed sources are never written or deleted.
    """
    now_utc = _aware(now) or datetime.now(timezone.utc)
    seed_root = repo_seed_root()
    seed_before = {}
    if seed_root.is_dir():
        for path in seed_root.rglob(SKILL_MD_NAME):
            try:
                seed_before[str(path)] = path.stat().st_mtime
            except OSError:
                continue

    classified: List[Dict[str, Any]] = []
    archived: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for pack_dir in _iter_live_pack_dirs(catalog):
        pack_id = pack_dir.name
        row: Dict[str, Any] = {"pack_id": pack_id, "path": str(pack_dir)}
        if is_bundled_pack(pack_id):
            row["status"] = STATUS_BUNDLED
            row["archived"] = False
            if auto_archive:
                skipped.append({**row, "reason": "bundled seed; never auto-archive"})
            classified.append(row)
            continue
        used = last_used_at(pack_dir, pack_id=pack_id, overrides=last_used_by_id)
        status = classify_age(
            used,
            now=now_utc,
            stale_days=stale_days,
            archive_days=archive_days,
        )
        row["status"] = status
        row["last_used"] = used.isoformat() if used else None
        row["archived"] = False
        if status == STATUS_UNKNOWN:
            skipped.append({**row, "reason": "unknown last-used; fail closed"})
            classified.append(row)
            continue
        if status == STATUS_ARCHIVE and auto_archive:
            moved = archive_pack(catalog, pack_id, confirm=confirm_bundled, now=now_utc)
            row["archived"] = bool(moved.get("archived"))
            row["move"] = moved
            if moved.get("archived"):
                archived.append(row)
            else:
                skipped.append({**row, "reason": moved.get("error")})
            classified.append(row)
            continue
        classified.append(row)

    seed_after_ok = True
    seed_touched: List[str] = []
    for path_text, mtime in seed_before.items():
        path = Path(path_text)
        if not path.is_file():
            seed_after_ok = False
            seed_touched.append(path_text)
            continue
        try:
            if path.stat().st_mtime != mtime:
                seed_after_ok = False
                seed_touched.append(path_text)
        except OSError:
            seed_after_ok = False
            seed_touched.append(path_text)

    return {
        "success": True,
        "source": SOURCE,
        "auto_archive": bool(auto_archive),
        "stale_days": int(stale_days),
        "archive_days": int(archive_days),
        "classified": classified,
        "archived": archived,
        "skipped": skipped,
        "archived_count": len(archived),
        "skill_md_deleted": False,
        "src_written": False,
        "repo_seeds_untouched": seed_after_ok,
        "repo_seeds_touched": seed_touched,
        "stream_turn_attached": False,
    }


def maybe_curate_from_routine(
    catalog: UserSkillCatalog,
    routine: Any = None,
    *,
    now: Optional[datetime] = None,
    last_used_by_id: Optional[Dict[str, Optional[datetime]]] = None,
) -> Dict[str, Any]:
    """Hook from skill-eval-sleep / sibling routine. Off unless metadata.auto_archive."""
    meta = dict(getattr(routine, "metadata", None) or {}) if routine is not None else {}
    auto = bool(meta.get("auto_archive", False))
    stale_days = int(meta.get("stale_days", STALE_AFTER_DAYS) or STALE_AFTER_DAYS)
    archive_days = int(meta.get("archive_days", ARCHIVE_AFTER_DAYS) or ARCHIVE_AFTER_DAYS)
    if not auto:
        return {
            "success": True,
            "skipped": True,
            "reason": "auto_archive is false; curator is not destructive by default.",
            "auto_archive": False,
            "archived_count": 0,
            "stream_turn_attached": False,
        }
    return curate_user_skill_packs(
        catalog,
        now=now,
        auto_archive=True,
        last_used_by_id=last_used_by_id,
        stale_days=stale_days,
        archive_days=archive_days,
    )


def run_curator_job(
    catalog: UserSkillCatalog,
    *,
    routine: Any = None,
    now: Optional[datetime] = None,
    last_used_by_id: Optional[Dict[str, Optional[datetime]]] = None,
) -> Dict[str, Any]:
    """Sibling routine entry. Still honors metadata.auto_archive (seeded True, routine paused)."""
    meta = dict(getattr(routine, "metadata", None) or {}) if routine is not None else {}
    auto = bool(meta.get("auto_archive", True)) if routine is not None else True
    stale_days = int(meta.get("stale_days", STALE_AFTER_DAYS) or STALE_AFTER_DAYS)
    archive_days = int(meta.get("archive_days", ARCHIVE_AFTER_DAYS) or ARCHIVE_AFTER_DAYS)
    result = curate_user_skill_packs(
        catalog,
        now=now,
        auto_archive=auto,
        last_used_by_id=last_used_by_id,
        stale_days=stale_days,
        archive_days=archive_days,
    )
    result["routine_id"] = ROUTINE_ID
    return result


def job_output_text(result: Dict[str, Any]) -> str:
    return json.dumps(
        {
            "status": "success" if result.get("success") else "failed",
            "auto_archive": result.get("auto_archive"),
            "archived_count": result.get("archived_count"),
            "archived": [row.get("pack_id") for row in (result.get("archived") or [])],
            "skill_md_deleted": False,
        },
        indent=2,
    )
