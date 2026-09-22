"""Backup and restore of the resolved data dir [REQ-DATA-007, REQ-DATA-008]."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Union

from src.infrastructure.data.resolver import DataDirPaths

logger = logging.getLogger(__name__)

SKIP_DIR_NAMES = frozenset({".git", ".venv", "venv", "__pycache__", "node_modules", "backups"})
DB_ARCHIVE_NAME = "autoreiv.db"
MANIFEST_NAME = "backup-manifest.json"


class DataDirRestoreError(ValueError):
    """Restore rejected. Live tree is left unchanged."""


class DataDirBackupService:
    """Zip or copy the data dir; confirmed restore replaces the tree."""

    def __init__(self, paths: DataDirPaths) -> None:
        self.paths = paths

    def resolve_backup_dir(self, custom_dir: Optional[Union[str, Path]] = None) -> Path:
        if custom_dir is not None and str(custom_dir).strip():
            return Path(str(custom_dir).strip()).expanduser()
        backups_path = getattr(self.paths, "backups_path", None)
        if backups_path is not None:
            return Path(backups_path)
        return self.paths.root / "backups"

    def default_backup_dest(
        self,
        now: Optional[datetime] = None,
        *,
        backup_dir: Optional[Union[str, Path]] = None,
    ) -> Path:
        ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
        bdir = self.resolve_backup_dir(backup_dir)
        candidate = bdir / f"autoreiv-data-{ts}.zip"
        if not candidate.exists():
            return candidate
        idx = 1
        while (bdir / f"autoreiv-data-{ts}_{idx}.zip").exists():
            idx += 1
        return bdir / f"autoreiv-data-{ts}_{idx}.zip"

    def backup(
        self,
        dest: Optional[Union[str, Path]] = None,
        *,
        backup_dir: Optional[Union[str, Path]] = None,
        now: Optional[datetime] = None,
    ) -> Path:
        dest_path = (
            Path(dest) if dest is not None else self.default_backup_dest(now=now, backup_dir=backup_dir)
        )
        dest_path = dest_path.expanduser()
        if dest_path.exists() and dest_path.is_dir():
            return self._backup_copy(dest_path)
        if dest_path.suffix.lower() != ".zip":
            dest_path = dest_path.with_suffix(dest_path.suffix + ".zip") if dest_path.suffix else dest_path.with_suffix(".zip")
        return self._backup_zip(dest_path)

    def list_backups(self, backup_dir: Optional[Union[str, Path]] = None) -> List[dict[str, Any]]:
        bdir = self.resolve_backup_dir(backup_dir)
        if not bdir.is_dir():
            return []
        items: List[dict[str, Any]] = []
        for file in bdir.iterdir():
            if not file.is_file() or file.suffix.lower() != ".zip":
                continue
            name = file.name
            if not (name.startswith("autoreiv-data-") or name.startswith("pre-restore-")):
                continue
            try:
                stat = file.stat()
            except OSError:
                continue

            iso_created = None
            m = re.search(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z", name)
            if m:
                iso_created = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}Z"
            else:
                iso_created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            size_bytes = stat.st_size
            size_mb = round(size_bytes / (1024 * 1024), 2)
            items.append({
                "filename": name,
                "size_bytes": size_bytes,
                "size_mb": size_mb,
                "created_at": iso_created,
                "path": str(file.resolve()),
                "is_pre_restore": name.startswith("pre-restore-"),
                "mtime": stat.st_mtime,
            })
        items.sort(key=lambda x: (x["created_at"], x["mtime"]), reverse=True)
        return items

    def prune_backups(
        self,
        retention_count: int,
        backup_dir: Optional[Union[str, Path]] = None,
    ) -> List[str]:
        if retention_count < 1:
            return []
        bdir = self.resolve_backup_dir(backup_dir)
        if not bdir.is_dir():
            return []
        candidates: List[tuple[str, float, Path]] = []
        for file in bdir.iterdir():
            if file.is_file() and file.name.startswith("autoreiv-data-") and file.name.endswith(".zip"):
                try:
                    stat = file.stat()
                    m = re.search(r"(\d{8}T\d{6}Z)", file.name)
                    ts_key = m.group(1) if m else ""
                    candidates.append((ts_key, stat.st_mtime, file))
                except OSError:
                    pass
        # Sort descending by filename timestamp then mtime (newest first)
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        to_prune = candidates[retention_count:]
        pruned_names: List[str] = []
        for _, _, file_path in to_prune:
            try:
                file_path.unlink()
                pruned_names.append(file_path.name)
                logger.info("Pruned old backup archive: %s", file_path)
            except OSError as exc:
                logger.warning("Failed to prune backup archive %s: %s", file_path, exc)
        return pruned_names

    def delete_backup(self, filename: str, backup_dir: Optional[Union[str, Path]] = None) -> bool:
        clean_name = str(filename or "").strip()
        if not clean_name or not clean_name.endswith(".zip"):
            return False
        if ".." in clean_name or "/" in clean_name or "\\" in clean_name:
            raise ValueError(f"Invalid backup filename: {clean_name}")
        bdir = self.resolve_backup_dir(backup_dir).resolve()
        target = (bdir / clean_name).resolve()
        if target.parent != bdir:
            raise ValueError(f"Path traversal detected: {clean_name}")
        if target.is_file():
            target.unlink()
            logger.info("Deleted backup archive: %s", target)
            return True
        return False

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
            bdir = self.resolve_backup_dir()
            bdir.mkdir(parents=True, exist_ok=True)
            pre_restore = bdir / f"pre-restore-{ts}.zip"
            self.paths.root.mkdir(parents=True, exist_ok=True)
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
        bdir_resolved = _try_resolve(self.resolve_backup_dir())
        for child in root.iterdir():
            if child.name == "backups":
                continue
            child_resolved = _try_resolve(child)
            if bdir_resolved is not None and child_resolved == bdir_resolved:
                continue
            return True
        return False


    def build_manifest(
        self,
        *,
        include_wiki_content: bool = False,
        written_members: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """ADR-0056 manifest: DBs, wiki URI, digests, pack set, provenance."""
        import hashlib

        from src.infrastructure.data.wiki_gate import configured_wiki_path, resolve_deploy_mode

        def _digest(path: Path) -> Optional[str]:
            if not path.is_file():
                return None
            h = hashlib.sha256()
            try:
                with open(path, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                return h.hexdigest()
            except OSError:
                return None

        wiki = configured_wiki_path() or self.paths.wiki_path
        packs = []
        packs_root = self.paths.packs_path
        if packs_root and Path(packs_root).is_dir():
            for sub in sorted(Path(packs_root).iterdir()):
                if not sub.is_dir():
                    continue
                entry: dict[str, Any] = {"agent_id": sub.name, "path": str(sub)}
                for suffix in ("_storage.db", "_memory.db"):
                    # snake-ish match
                    for db in sub.glob(f"*{suffix}"):
                        role = "storage" if suffix.endswith("storage.db") else "memory"
                        entry.setdefault("databases", []).append(
                            {"role": role, "path": str(db), "sha256": _digest(db)}
                        )
                if (sub / "pack.json").is_file():
                    entry["pack_json"] = True
                packs.append(entry)

        manifest = {
            "schema_version": 1,
            "kind": "autoreiv-backup-manifest",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "deploy_mode": resolve_deploy_mode(),
            "data_root": str(self.paths.root),
            "operational_db": {
                "role": "operational",
                "path": str(self.paths.db_path),
                "sha256": _digest(self.paths.db_path) if self.paths.db_path.is_file() else None,
            },
            "wiki": {
                "uri": str(wiki) if wiki else None,
                "include_content": bool(include_wiki_content),
                "sha256": None,
            },
            "packs": packs,
            "members": sorted(written_members) if written_members else [],
            "provenance": {
                "app": "AutoReiv",
                "adr": "0056",
                "card": "CARD-414",
            },
        }
        return manifest

    def _write_manifest_member(self, zf: zipfile.ZipFile, written: set[str], *, include_wiki_content: bool = False) -> None:
        manifest = self.build_manifest(include_wiki_content=include_wiki_content, written_members=written)
        payload = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        zf.writestr(MANIFEST_NAME, payload)
        written.add(MANIFEST_NAME)

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
                self._write_manifest_member(zf, written)
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
        bdir_resolved = _try_resolve(self.resolve_backup_dir())
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            current_dir = Path(dirpath)
            current_dir_resolved = _try_resolve(current_dir)
            if bdir_resolved is not None and current_dir_resolved is not None:
                if current_dir_resolved == bdir_resolved or _is_subpath(current_dir_resolved, bdir_resolved):
                    continue
            for name in filenames:
                path = current_dir / name
                path_resolved = _try_resolve(path)
                if dest_resolved is not None and path_resolved == dest_resolved:
                    continue
                if bdir_resolved is not None and path_resolved is not None:
                    if path_resolved == bdir_resolved or _is_subpath(path_resolved, bdir_resolved):
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
        tree = _find_tree_root(staging)
        manifest_path = tree / MANIFEST_NAME
        if not manifest_path.is_file():
            # nested?
            alt = staging / MANIFEST_NAME
            if alt.is_file():
                manifest_path = alt
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                wiki_uri = (manifest.get("wiki") or {}).get("uri")
                if wiki_uri:
                    logger.info("Restore manifest wiki URI: %s (will not invent a second wiki)", wiki_uri)
            except (json.JSONDecodeError, OSError) as exc:
                raise DataDirRestoreError(f"Invalid backup-manifest.json: {exc}") from exc
        return tree

    def _replace_tree(self, source_tree: Path) -> None:
        root = self.paths.root
        root.mkdir(parents=True, exist_ok=True)
        dest_db = self.paths.db_path
        dest_db.parent.mkdir(parents=True, exist_ok=True)
        bdir_resolved = _try_resolve(self.resolve_backup_dir())
        source_db = source_tree / "database" / DB_ARCHIVE_NAME
        if not source_db.is_file():
            source_db = source_tree / DB_ARCHIVE_NAME
        if source_db.is_file():
            _snapshot_sqlite(source_db, dest_db)
        for child in list(root.iterdir()):
            if child.name in {"backups", DB_ARCHIVE_NAME, "database"}:
                continue
            child_resolved = _try_resolve(child)
            if bdir_resolved is not None and child_resolved == bdir_resolved:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
        for child in source_tree.iterdir():
            if child.name in {"backups", DB_ARCHIVE_NAME, "database"}:
                continue
            child_resolved = _try_resolve(child)
            if bdir_resolved is not None and child_resolved == bdir_resolved:
                continue
            target = root / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)


def _is_subpath(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


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
