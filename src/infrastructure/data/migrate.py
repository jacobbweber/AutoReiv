"""Operator-driven data-dir relocate [CARD-313].

Copy current root → destination, validate, rename old to *_backup_<ts>,
persist AUTOREIV_DATA_DIR so the next resolve uses the new path.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.infrastructure.data.resolver import (
    BACKUP_DIR_SETTING_KEY,
    BACKUP_RETENTION_SETTING_KEY,
    BACKUP_SCHEDULE_SETTING_KEY,
    DATA_DIR_SETTING_KEY,
    ENV_BACKUP_DIR,
    ENV_DATA_DIR,
    DataDirPaths,
    ensure_live_data_root,
    is_checkout_live_tree_path,
    repo_root,
)

logger = logging.getLogger(__name__)

_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "*.pyc",
)


class DataDirRelocateError(ValueError):
    """Migrate rejected; live tree left at the source root."""


@dataclass(frozen=True)
class DataDirMigrateResult:
    source: Path
    destination: Path
    backup_path: Optional[Path]
    persisted_via: list[str]


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(
            os.path.normpath(str(right))
        )


def _is_empty_dir(path: Path) -> bool:
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    return next(path.iterdir(), None) is None


def validate_data_dir_tree(root: Path) -> None:
    """Require a recognizable AutoReiv data layout (db and/or wiki/skills)."""
    if not root.is_dir():
        raise DataDirRelocateError(f"Destination is not a directory: {root}")
    markers = (
        root / "database" / "autoreiv.db",
        root / "autoreiv.db",
        root / "wiki",
        root / "skills",
        root / "packs",
    )
    if not any(m.exists() for m in markers):
        raise DataDirRelocateError(
            f"Destination does not look like an AutoReiv data dir (no db/wiki/skills/packs): {root}"
        )


def _find_repo_dotenv(checkout: Path) -> Path:
    return checkout / ".env"


def persist_autoreiv_data_dir(dest: Path, *, checkout: Optional[Path] = None) -> list[str]:
    """Write AUTOREIV_DATA_DIR to repo .env + settings row; set process env.

    Prefer the user-visible `.env` the app already loads via load_repo_dotenv,
    and the SQLite `data_dir` setting the resolver peeks when env is unset.
    """
    dest_str = str(dest.expanduser().resolve())
    persisted: list[str] = []
    root = checkout or repo_root()

    env_path = _find_repo_dotenv(root)
    try:
        _upsert_dotenv_key(env_path, ENV_DATA_DIR, dest_str)
        persisted.append(f".env:{env_path}")
    except OSError as exc:
        logger.warning("Could not write %s: %s", env_path, exc)

    os.environ[ENV_DATA_DIR] = dest_str
    persisted.append("process:AUTOREIV_DATA_DIR")

    db_candidates = (
        dest / "database" / "autoreiv.db",
        dest / "autoreiv.db",
    )
    for db_path in db_candidates:
        if db_path.is_file():
            try:
                _write_sqlite_setting(db_path, DATA_DIR_SETTING_KEY, dest_str)
                persisted.append(f"settings:{db_path}")
                break
            except (sqlite3.Error, OSError) as exc:
                logger.warning("Could not persist data_dir setting in %s: %s", db_path, exc)

    return persisted


def _upsert_dotenv_key(env_path: Path, key: str, value: str) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    replaced = False
    out: list[str] = []
    for line in lines:
        if pattern.match(line):
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append("# CARD-313: relocated user data root")
        out.append(f"{key}={value}")
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    env_path.write_text(text, encoding="utf-8")


def _remove_dotenv_key(env_path: Path, key: str) -> None:
    if not env_path.is_file():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    out = [line for line in lines if not pattern.match(line)]
    text = "\n".join(out)
    if text and not text.endswith("\n"):
        text += "\n"
    env_path.write_text(text, encoding="utf-8")


def _write_sqlite_setting(db_path: Path, key: str, value: str) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value_json TEXT NOT NULL, "
            "updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        cols = {r[1] for r in conn.execute("PRAGMA table_info(settings)").fetchall()}
        payload = json.dumps(value)
        if "updated_at" in cols:
            conn.execute(
                "INSERT INTO settings(key, value_json, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, "
                "updated_at=CURRENT_TIMESTAMP",
                (key, payload),
            )
        else:
            conn.execute(
                "INSERT INTO settings(key, value_json) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json",
                (key, payload),
            )
        conn.commit()
    finally:
        conn.close()


def migrate_data_dir(
    source: Path,
    destination: str | Path,
    *,
    checkout: Optional[Path] = None,
) -> DataDirMigrateResult:
    """Copy source → dest, validate, persist path, rename source to *_backup_<ts>."""
    checkout_root = checkout or repo_root()
    src = Path(source).expanduser().resolve()
    if not src.is_dir():
        raise DataDirRelocateError(f"Source data dir does not exist: {src}")

    dest = Path(destination).expanduser()
    if not str(destination).strip():
        raise DataDirRelocateError("Destination path is required")
    try:
        dest = dest.resolve()
    except OSError:
        dest = dest.absolute()

    if _same_path(src, dest):
        raise DataDirRelocateError("Destination must differ from the current data dir")

    if is_checkout_live_tree_path(dest, checkout=checkout_root):
        raise DataDirRelocateError(
            f"Refusing destination inside git checkout: {dest}. "
            "Use a user-data path outside the repo (or scratch/ for temp only)."
        )
    try:
        ensure_live_data_root(dest, checkout=checkout_root)
    except ValueError as exc:
        raise DataDirRelocateError(str(exc)) from exc

    # Refuse nesting either way (do not catch DataDirRelocateError — it subclasses ValueError)
    try:
        dest.relative_to(src)
    except ValueError:
        pass
    else:
        raise DataDirRelocateError("Destination cannot be inside the source data dir")
    try:
        src.relative_to(dest)
    except ValueError:
        pass
    else:
        raise DataDirRelocateError("Destination cannot be a parent of the source data dir")

    if dest.exists() and not _is_empty_dir(dest):
        raise DataDirRelocateError(
            f"Destination already exists and is not empty: {dest}. "
            "Choose an empty or new path."
        )

    if dest.exists() and _is_empty_dir(dest):
        dest.rmdir()

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(src, dest, ignore=_COPY_IGNORE, dirs_exist_ok=False)
    except OSError as exc:
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        raise DataDirRelocateError(f"Copy failed: {exc}") from exc

    try:
        validate_data_dir_tree(dest)
    except DataDirRelocateError:
        shutil.rmtree(dest, ignore_errors=True)
        raise

    persisted = persist_autoreiv_data_dir(dest, checkout=checkout_root)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = src.parent / f"{src.name}_backup_{ts}"
    if backup_path.exists():
        backup_path = src.parent / f"{src.name}_backup_{ts}_{os.getpid()}"
    try:
        shutil.move(str(src), str(backup_path))
    except OSError as exc:
        logger.warning(
            "Copied and persisted %s but could not rename source %s → %s: %s",
            dest,
            src,
            backup_path,
            exc,
        )
        return DataDirMigrateResult(
            source=src,
            destination=dest,
            backup_path=None,
            persisted_via=persisted + [f"rename_failed:{exc}"],
        )

    logger.info(
        "Migrated data dir %s → %s (backup %s); persisted via %s",
        src,
        dest,
        backup_path,
        persisted,
    )
    return DataDirMigrateResult(
        source=src,
        destination=dest,
        backup_path=backup_path,
        persisted_via=persisted,
    )


def resolve_paths_for_root(root: Path) -> DataDirPaths:
    """Build DataDirPaths for an already-migrated root (explicit layout)."""
    root = Path(root).expanduser().resolve()
    return DataDirPaths(
        root=root,
        db_path=root / "database" / "autoreiv.db"
        if (root / "database" / "autoreiv.db").exists()
        else root / "autoreiv.db",
        wiki_path=root / "wiki",
        skills_path=root / "skills",
        agents_path=root / "agents",
        job_templates_path=root / "templates" / "jobs",
        packs_path=root / "packs",
        backups_path=root / "backups",
    )


def persist_autoreiv_backup_config(
    *,
    backup_dir: Optional[str] = None,
    schedule: Optional[str] = None,
    retention: Optional[int] = None,
    checkout: Optional[Path] = None,
    store: Optional[object] = None,
) -> list[str]:
    """Persist backup directory, schedule cadence, and retention policy [CARD-404]."""
    checkout_root = checkout or repo_root()
    env_path = _find_repo_dotenv(checkout_root)
    persisted: list[str] = []

    if backup_dir is not None:
        clean_dir = str(backup_dir).strip()
        if clean_dir:
            p = Path(clean_dir).expanduser()
            if is_checkout_live_tree_path(p, checkout=checkout_root):
                raise ValueError(
                    f"Refusing backup dir inside git checkout: {clean_dir}. "
                    "Use a path outside the repository or under scratch/."
                )
            resolved_str = str(p.resolve())
            try:
                _upsert_dotenv_key(env_path, ENV_BACKUP_DIR, resolved_str)
                persisted.append(f".env:{env_path}")
            except OSError as exc:
                logger.warning("Could not write %s to %s: %s", ENV_BACKUP_DIR, env_path, exc)
            os.environ[ENV_BACKUP_DIR] = resolved_str
            persisted.append("process:AUTOREIV_BACKUP_DIR")
            if store is not None and hasattr(store, "set_setting"):
                store.set_setting(BACKUP_DIR_SETTING_KEY, resolved_str)
                persisted.append("settings:backup_dir")
        else:
            try:
                _remove_dotenv_key(env_path, ENV_BACKUP_DIR)
                persisted.append(f".env:removed:{ENV_BACKUP_DIR}")
            except OSError as exc:
                logger.warning("Could not remove %s from %s: %s", ENV_BACKUP_DIR, env_path, exc)
            os.environ.pop(ENV_BACKUP_DIR, None)
            persisted.append("process:cleared:AUTOREIV_BACKUP_DIR")
            if store is not None and hasattr(store, "set_setting"):
                store.set_setting(BACKUP_DIR_SETTING_KEY, None)
                persisted.append("settings:cleared:backup_dir")

    if schedule is not None:
        clean_sched = str(schedule).strip().lower()
        if store is not None and hasattr(store, "set_setting"):
            store.set_setting(BACKUP_SCHEDULE_SETTING_KEY, clean_sched)
            persisted.append(f"settings:backup_schedule:{clean_sched}")

    if retention is not None:
        ret_val = max(1, int(retention))
        if store is not None and hasattr(store, "set_setting"):
            store.set_setting(BACKUP_RETENTION_SETTING_KEY, ret_val)
            persisted.append(f"settings:backup_retention:{ret_val}")

    return persisted
