"""
Data directory resolution and first-boot copy-migrate [REQ-DATA-001 - REQ-DATA-006].

User-owned state lives outside the git checkout (user data outside git).
Resolution: AUTOREIV_DATA_DIR env > persisted setting data_dir > platform default.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from src.infrastructure.skills.platform_packs import seed_platform_pack_folders
from src.infrastructure.skills.seed import seed_bundled_skill_packs

logger = logging.getLogger(__name__)

DATA_DIR_SETTING_KEY = "data_dir"
ENV_DATA_DIR = "AUTOREIV_DATA_DIR"
ENV_DB_PATH = "AUTOREIV_DB_PATH"
ENV_WIKI_PATH = "AUTOREIV_WIKI_PATH"

_LEGACY_DB_REL = Path("data") / "autoreiv.db"
_LEGACY_WIKI_REL = Path("data") / "wiki"
_LEGACY_DB_STRINGS = frozenset({"./data/autoreiv.db", "data/autoreiv.db", ".\\data\\autoreiv.db", "data\\autoreiv.db"})
_LEGACY_WIKI_STRINGS = frozenset({"./data/wiki", "data/wiki", ".\\data\\wiki", "data\\wiki"})


class DataDirMigrationError(RuntimeError):
    """Raised when a first-boot copy fails. Dest is not opened as a new empty store."""


@dataclass(frozen=True)
class DataDirPaths:
    root: Path
    db_path: Path
    wiki_path: Path
    skills_path: Path
    agents_path: Path
    job_templates_path: Path
    packs_path: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.packs_path is None:
            object.__setattr__(self, "packs_path", self.root / "packs")


def repo_root() -> Path:
    """Git checkout root (src/infrastructure/data/resolver.py -> parents[3])."""
    return Path(__file__).resolve().parents[3]


def _is_docker_runtime() -> bool:
    return Path("/.dockerenv").exists()


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return os.path.normcase(os.path.normpath(str(left))) == os.path.normcase(os.path.normpath(str(right)))


def _is_empty_dir(path: Path) -> bool:
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    return next(path.iterdir(), None) is None


def _normalize_env_path(raw: str) -> str:
    return raw.strip().replace("\\", "/").rstrip("/")


class DataDirResolver:
    """Resolve AUTOREIV_DATA_DIR and copy-migrate live checkout data without wipe."""

    def __init__(
        self,
        *,
        setting_data_dir: Optional[str] = None,
        checkout_root: Optional[Path] = None,
        in_docker: Optional[bool] = None,
        home: Optional[Path] = None,
        local_appdata: Optional[Path] = None,
        os_name: Optional[str] = None,
    ) -> None:
        self.setting_data_dir = setting_data_dir
        self.checkout_root = Path(checkout_root) if checkout_root is not None else repo_root()
        self.in_docker = _is_docker_runtime() if in_docker is None else in_docker
        self.os_name = os.name if os_name is None else os_name
        self.home = Path(home) if home is not None else Path.home()
        if local_appdata is not None:
            self.local_appdata = Path(local_appdata)
        elif os.environ.get("LOCALAPPDATA"):
            self.local_appdata = Path(os.environ["LOCALAPPDATA"])
        else:
            self.local_appdata = self.home / "AppData" / "Local"

    def platform_default(self) -> Path:
        if self.in_docker:
            return Path("/data")
        if self.os_name == "nt":
            return self.local_appdata / "AutoReiv"
        return self.home / ".autoreiv"

    def legacy_db_path(self) -> Path:
        return self.checkout_root / _LEGACY_DB_REL

    def legacy_wiki_path(self) -> Path:
        return self.checkout_root / _LEGACY_WIKI_REL

    def _is_legacy_db(self, path: Path, raw: str) -> bool:
        if raw.strip() in _LEGACY_DB_STRINGS or _normalize_env_path(raw) in {
            "./data/autoreiv.db",
            "data/autoreiv.db",
        }:
            return True
        return _same_path(path, self.legacy_db_path())

    def _is_legacy_wiki(self, path: Path, raw: str) -> bool:
        if raw.strip() in _LEGACY_WIKI_STRINGS or _normalize_env_path(raw) in {"./data/wiki", "data/wiki"}:
            return True
        return _same_path(path, self.legacy_wiki_path())

    def _explicit_db_path(self) -> Optional[Path]:
        raw = os.environ.get(ENV_DB_PATH)
        if raw is None or not str(raw).strip():
            return None
        stripped = str(raw).strip()
        if stripped == ":memory:":
            return Path(":memory:")
        path = Path(stripped).expanduser()
        if self._is_legacy_db(path, stripped):
            return None
        return path

    def _explicit_wiki_path(self) -> Optional[Path]:
        raw = os.environ.get(ENV_WIKI_PATH)
        if raw is None or not str(raw).strip():
            return None
        stripped = str(raw).strip()
        path = Path(stripped).expanduser()
        if self._is_legacy_wiki(path, stripped):
            return None
        return path

    def _peek_setting_data_dir(self) -> Optional[str]:
        candidates = (
            self.platform_default() / "database" / "autoreiv.db",
            self.platform_default() / "autoreiv.db",
            self.legacy_db_path(),
        )
        for db_path in candidates:
            value = _read_sqlite_setting(db_path, DATA_DIR_SETTING_KEY)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def resolve_root(self) -> Path:
        env = os.environ.get(ENV_DATA_DIR)
        if env is not None and str(env).strip():
            return Path(str(env).strip()).expanduser()
        if self.setting_data_dir is not None and str(self.setting_data_dir).strip():
            return Path(str(self.setting_data_dir).strip()).expanduser()
        peeked = self._peek_setting_data_dir()
        if peeked:
            return Path(peeked).expanduser()
        return self.platform_default()

    def resolve(self) -> DataDirPaths:
        root = self.resolve_root()
        explicit_db = self._explicit_db_path()
        explicit_wiki = self._explicit_wiki_path()
        db_path = explicit_db if explicit_db is not None else root / "database" / "autoreiv.db"
        wiki_path = explicit_wiki if explicit_wiki is not None else root / "wiki"
        return DataDirPaths(
            root=root,
            db_path=db_path,
            wiki_path=wiki_path,
            skills_path=root / "skills",
            agents_path=root / "agents",
            job_templates_path=root / "templates" / "jobs",
            packs_path=root / "packs",
        )

    def ensure_layout(self, paths: DataDirPaths) -> None:
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.db_path.parent.mkdir(parents=True, exist_ok=True)
        paths.wiki_path.mkdir(parents=True, exist_ok=True)
        paths.skills_path.mkdir(parents=True, exist_ok=True)
        paths.agents_path.mkdir(parents=True, exist_ok=True)
        paths.job_templates_path.mkdir(parents=True, exist_ok=True)
        paths.packs_path.mkdir(parents=True, exist_ok=True)

    def _db_migrate_source(self, dest_db: Path) -> Optional[Path]:
        explicit = self._explicit_db_path()
        if explicit is not None:
            if str(explicit) == ":memory:":
                return None
            if explicit.exists() and not _same_path(explicit, dest_db):
                return explicit
            return None
        legacy = self.legacy_db_path()
        env_raw = os.environ.get(ENV_DB_PATH)
        if env_raw and str(env_raw).strip() and str(env_raw).strip() != ":memory:":
            env_path = Path(str(env_raw).strip()).expanduser()
            if env_path.exists() and self._is_legacy_db(env_path, env_raw):
                legacy = env_path
        if legacy.is_file() and not _same_path(legacy, dest_db):
            return legacy
        return None

    def _wiki_migrate_source(self, dest_wiki: Path) -> Optional[Path]:
        explicit = self._explicit_wiki_path()
        if explicit is not None:
            if explicit.exists() and explicit.is_dir() and not _same_path(explicit, dest_wiki):
                if _is_empty_dir(explicit):
                    return None
                return explicit
            return None
        legacy = self.legacy_wiki_path()
        env_raw = os.environ.get(ENV_WIKI_PATH)
        if env_raw and str(env_raw).strip():
            env_path = Path(str(env_raw).strip()).expanduser()
            if env_path.exists() and self._is_legacy_wiki(env_path, env_raw):
                legacy = env_path
        if legacy.is_dir() and not _is_empty_dir(legacy) and not _same_path(legacy, dest_wiki):
            return legacy
        return None

    def migrate_if_needed(self, paths: DataDirPaths) -> None:
        """Copy live checkout db/wiki or relocate root autoreiv.db into database/. Never wipe source."""
        dest_db = paths.root / "database" / "autoreiv.db"
        dest_wiki = paths.root / "wiki"

        # Step 1: Relocate legacy root / "autoreiv.db" to paths.db_path if present and dest doesn't exist
        root_db = paths.root / "autoreiv.db"
        if root_db.is_file() and not dest_db.exists() and not _same_path(root_db, dest_db):
            self._move_db_files(root_db, dest_db)

        source_db = self._db_migrate_source(dest_db)
        if source_db is not None and not dest_db.exists():
            self._copy_db(source_db, dest_db)

        source_wiki = self._wiki_migrate_source(dest_wiki)
        if source_wiki is not None and _is_empty_dir(dest_wiki):
            self._copy_wiki(source_wiki, dest_wiki)

    def _move_db_files(self, source: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(source), str(dest))
            logger.info("Relocated database %s -> %s", source, dest)
            for ext in ("-wal", "-shm"):
                sidecar = Path(f"{source}{ext}")
                if sidecar.exists():
                    shutil.move(str(sidecar), str(f"{dest}{ext}"))
                    logger.info("Relocated sidecar %s -> %s", sidecar, f"{dest}{ext}")
        except Exception as exc:
            logger.warning("Could not move %s to %s: %s; falling back to copy", source, dest, exc)
            self._copy_db(source, dest)

    def _copy_db(self, source: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".migrating")
        try:
            if tmp.exists():
                tmp.unlink()
            shutil.copy2(source, tmp)
            tmp.replace(dest)
            logger.info("Copied live database %s -> %s (source left in place)", source, dest)
        except Exception as exc:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if dest.exists() and dest.stat().st_size == 0:
                try:
                    dest.unlink()
                except OSError:
                    pass
            raise DataDirMigrationError(
                f"Failed to copy database from {source} to {dest}; source left in place"
            ) from exc

    def _copy_wiki(self, source: Path, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        try:
            for item in source.iterdir():
                target = dest / item.name
                if target.exists():
                    continue
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            logger.info("Copied live wiki %s -> %s (source left in place)", source, dest)
        except Exception as exc:
            raise DataDirMigrationError(
                f"Failed to copy wiki from {source} to {dest}; source left in place"
            ) from exc


def _read_sqlite_setting(db_path: Path, key: str) -> Optional[object]:
    if not db_path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        try:
            conn = sqlite3.connect(str(db_path))
        except sqlite3.Error:
            return None
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        )
        if cur.fetchone() is None:
            return None
        cur = conn.execute("SELECT value_json FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row["value_json"])
    except (sqlite3.Error, json.JSONDecodeError, TypeError):
        return None
    finally:
        conn.close()


def bootstrap_data_dir(
    *,
    checkout_root: Optional[Path] = None,
    setting_data_dir: Optional[str] = None,
    migrate: bool = True,
) -> DataDirPaths:
    """Resolve, ensure layout, and optionally copy-migrate. Used by app and CLI."""
    resolver = DataDirResolver(checkout_root=checkout_root, setting_data_dir=setting_data_dir)
    paths = resolver.resolve()
    resolver.ensure_layout(paths)
    if migrate:
        resolver.migrate_if_needed(paths)
    seed_bundled_skill_packs(paths.skills_path)
    seed_platform_pack_folders(paths.root / "packs", checkout_root=resolver.checkout_root)
    return paths


def _agent_id_to_snake_case(agent_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", str(agent_id).strip()).strip("_").lower()
    return cleaned or "agent"


def resolve_agent_storage_path(
    agent_id: str,
    data_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Resolve the dedicated storage database path for an agent with snake_case filename [CARD-148]."""
    if data_dir is not None:
        root = Path(data_dir)
    else:
        root = DataDirResolver().resolve().root
    safe_id = "".join(c for c in str(agent_id).strip() if c.isalnum() or c in "._-")
    snake_id = _agent_id_to_snake_case(agent_id)
    db_filename = f"{snake_id}_storage.db"
    pack_dir = root / "packs" / safe_id
    target_path = pack_dir / db_filename

    # Migrate any previously named candidate files to target_path
    candidates_to_migrate = [
        pack_dir / "storage.db",
        root / "agents" / safe_id / "storage.db",
        root / "agents" / safe_id / db_filename,
    ]
    for candidate in candidates_to_migrate:
        if candidate.exists() and not target_path.exists():
            pack_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(candidate), str(target_path))
                for ext in ("-wal", "-shm"):
                    sidecar = Path(f"{candidate}{ext}")
                    if sidecar.exists():
                        shutil.move(str(sidecar), str(f"{target_path}{ext}"))
            except Exception:
                shutil.copy2(candidate, target_path)
            break

    return target_path


def get_agent_storage_connection(
    agent_id: str,
    data_dir: Optional[Union[str, Path]] = None,
) -> sqlite3.Connection:
    """Open an isolated SQLite connection to the agent's dedicated database [CARD-148]."""
    db_path = resolve_agent_storage_path(agent_id, data_dir=data_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    return conn


def resolve_agent_memory_path(
    agent_id: str,
    data_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Resolve the dedicated cognitive memory brain database path for an agent [CARD-116].

    Distinct from resolve_agent_storage_path (<slug>_storage.db), which is reserved
    for domain application data (e.g. finance tables). This database (<slug>_memory.db)
    is reserved exclusively for the agent's cognitive brain (pinned facts, episodic
    summaries, and semantic facts with decay curves).
    """
    if data_dir is not None:
        root = Path(data_dir)
    else:
        root = DataDirResolver().resolve().root
    safe_id = "".join(c for c in str(agent_id).strip() if c.isalnum() or c in "._-")
    snake_id = _agent_id_to_snake_case(agent_id)
    db_filename = f"{snake_id}_memory.db"
    pack_dir = root / "packs" / safe_id
    return pack_dir / db_filename

