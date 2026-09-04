"""Backup and restore of the resolved data dir [REQ-DATA-007, REQ-DATA-008]."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.infrastructure.data.resolver import DataDirPaths

logger = logging.getLogger(__name__)

SKIP_DIR_NAMES = frozenset({".git", ".venv", "venv", "__pycache__", "node_modules", "backups"})
DB_ARCHIVE_NAME = "autoreiv.db"


class DataDirRestoreError(ValueError):
    """Restore rejected. Live tree is left unchanged."""


class DataDirBackupService:
    """Zip or copy the data dir; confirmed restore replaces the tree."""

    def __init__(self, paths: DataDirPaths) -> None:
        self.paths = paths

    def default_backup_dest(self, now: Optional[datetime] = None) -> Path:
        ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
        return self.paths.root / "backups" / f"autoreiv-data-{ts}.zip"

    def backup(self, dest: Optional[Path] = None) -> Path:
        dest_path = Path(dest) if dest is not None else self.default_backup_dest()
        dest_path = dest_path.expanduser()
        if dest_path.exists() and dest_path.is_dir():
            return self._backup_copy(dest_path)
        if dest_path.suffix.lower() != ".zip":
            dest_path = dest_path.with_suffix(dest_path.suffix + ".zip") if dest_path.suffix else dest_path.with_suffix(".zip")
        return self._backup_zip(dest_path)

    def restore(self, src: Path, *, confirm: bool) -> None:
        if not confirm:
            logger.info("Restore cancelled (confirm=false); live tree unchanged")
            return
        src_path = Path(src).expanduser()
        if not src_path.is_file():
            raise DataDirRestoreError(f"Backup archive not found: {src_path}")
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        staging = self.paths.root.parent / f".{self.paths.root.name}.restore-staging-{ts}"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        try:
            tree = self._extract_and_validate(src_path, staging)
            pre_restore = self.paths.root / "backups" / f"pre-restore-{ts}.zip"
            self.paths.root.mkdir(parents=True, exist_ok=True)
            (self.paths.root / "backups").mkdir(parents=True, exist_ok=True)
            if self._tree_has_live_files():
                self._backup_zip(pre_restore)
            self._replace_tree(tree)
            logger.info("Restored data dir %s from %s (pre-restore: %s)", self.paths.root, src_path, pre_restore)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def _tree_has_live_files(self) -> bool:
        root = self.paths.root
        if not root.is_dir():
            return False
        for child in root.iterdir():
            if child.name == "backups":
                continue
            return True
        return False

    def _backup_zip(self, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".partial")
        try:
            if tmp.exists():
                tmp.unlink()
            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                written = set()
                for path, arcname in self._iter_backup_members(dest):
                    if arcname in written:
                        continue
                    if self._is_db_file(path) or Path(arcname).name == DB_ARCHIVE_NAME:
                        self._write_sqlite_member(zf, path, arcname)
                    else:
                        zf.write(path, arcname=arcname)
                    written.add(arcname)
                rel_db = self.paths.db_path.name
                try:
                    rel_db = self.paths.db_path.relative_to(self.paths.root).as_posix()
                except ValueError:
                    pass
                if rel_db not in written and DB_ARCHIVE_NAME not in written:
                    db = self.paths.db_path
                    if db.is_file() and str(db) != ":memory:":
                        self._write_sqlite_member(zf, db, rel_db)
                        written.add(rel_db)
                self._add_external_wiki(zf, written)
            tmp.replace(dest)
            logger.info("Wrote data dir backup %s", dest)
            return dest
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            raise

    def _backup_copy(self, dest: Path) -> Path:
        dest.mkdir(parents=True, exist_ok=True)
        for path, arcname in self._iter_backup_members(dest):
            target = dest / Path(arcname)
            target.parent.mkdir(parents=True, exist_ok=True)
            if self._is_db_file(path) or Path(arcname).name == DB_ARCHIVE_NAME:
                _snapshot_sqlite(path, target)
            elif path.is_dir():
                continue
            else:
                shutil.copy2(path, target)
        db = self.paths.db_path
        if db.is_file() and str(db) != ":memory:" and not (dest / DB_ARCHIVE_NAME).exists():
            _snapshot_sqlite(db, dest / DB_ARCHIVE_NAME)
        logger.info("Copied data dir backup to %s", dest)
        return dest

    def _iter_backup_members(self, dest: Path):
        root = self.paths.root
        if not root.exists():
            return
        dest_resolved = _try_resolve(dest)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for name in filenames:
                path = Path(dirpath) / name
                if dest_resolved is not None and _try_resolve(path) == dest_resolved:
                    continue
                try:
                    rel = path.relative_to(root)
                except ValueError:
                    continue
                yield path, rel.as_posix()

    def _add_external_wiki(self, zf: zipfile.ZipFile, written: set[str]) -> None:
        wiki = self.paths.wiki_path
        root = self.paths.root
        if not wiki.is_dir():
            return
        try:
            wiki.relative_to(root)
            return
        except ValueError:
            pass
        for dirpath, dirnames, filenames in os.walk(wiki):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for name in filenames:
                path = Path(dirpath) / name
                rel = Path("wiki") / path.relative_to(wiki)
                arcname = rel.as_posix()
                if arcname in written:
                    continue
                zf.write(path, arcname=arcname)
                written.add(arcname)

    def _is_db_file(self, path: Path) -> bool:
        db = self.paths.db_path
        if str(db) == ":memory:" or not db.exists():
            return path.name == DB_ARCHIVE_NAME
        left = _try_resolve(path)
        right = _try_resolve(db)
        if left is not None and right is not None:
            return left == right
        return path.name == DB_ARCHIVE_NAME

    def _write_sqlite_member(self, zf: zipfile.ZipFile, src: Path, arcname: str) -> None:
        fd, tmp_name = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            _snapshot_sqlite(src, tmp_path)
            zf.write(tmp_path, arcname=arcname)
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    def _extract_and_validate(self, src: Path, staging: Path) -> Path:
        staging.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(src, "r") as zf:
                _safe_extract(zf, staging)
        except zipfile.BadZipFile as exc:
            raise DataDirRestoreError(f"Not a valid zip archive: {src}") from exc
        return _find_tree_root(staging)

    def _replace_tree(self, source_tree: Path) -> None:
        root = self.paths.root
        root.mkdir(parents=True, exist_ok=True)
        dest_db = self.paths.db_path
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        source_db = source_tree / "database" / DB_ARCHIVE_NAME
        if not source_db.is_file():
            source_db = source_tree / DB_ARCHIVE_NAME
        if source_db.is_file():
            _snapshot_sqlite(source_db, dest_db)
        for child in list(root.iterdir()):
            if child.name in {"backups", DB_ARCHIVE_NAME, "database"}:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        for child in source_tree.iterdir():
            if child.name in {"backups", DB_ARCHIVE_NAME, "database"}:
                continue
            target = root / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)


def _try_resolve(path: Path) -> Optional[Path]:
    try:
        return path.resolve()
    except OSError:
        return None


def _snapshot_sqlite(src: Path, dest: Path) -> None:
    """Consistent SQLite snapshot; falls back to copy2 for non-db files."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        src_conn = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        shutil.copy2(src, dest)
        return
    try:
        src_conn.execute("PRAGMA page_count")
        dest_conn = sqlite3.connect(str(dest))
        try:
            src_conn.backup(dest_conn)
            dest_conn.commit()
        finally:
            dest_conn.close()
    except sqlite3.Error:
        shutil.copy2(src, dest)
    finally:
        src_conn.close()


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for info in zf.infolist():
        name = info.filename.replace("\\", "/").lstrip("/")
        if not name or name.endswith("/"):
            target_dir = dest / name
            _jail_under(dest, target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            continue
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts:
            raise DataDirRestoreError(f"Illegal path in archive: {info.filename}")
        target = dest / rel
        _jail_under(dest, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)


def _jail_under(root: Path, target: Path) -> None:
    root_resolved = root.resolve()
    try:
        target_resolved = target.resolve()
    except OSError:
        target_resolved = target
    try:
        target_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise DataDirRestoreError(f"Illegal path in archive: {target}") from exc


def _find_tree_root(staging: Path) -> Path:
    if (staging / DB_ARCHIVE_NAME).is_file() or (staging / "database" / DB_ARCHIVE_NAME).is_file():
        return staging
    children = list(staging.iterdir())
    dirs = [p for p in children if p.is_dir()]
    files = [p for p in children if p.is_file()]
    if len(dirs) == 1 and not files:
        nested = dirs[0]
        if (nested / DB_ARCHIVE_NAME).is_file() or (nested / "database" / DB_ARCHIVE_NAME).is_file():
            return nested
    raise DataDirRestoreError("Restore zip is missing autoreiv.db")
