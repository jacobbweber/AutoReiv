"""
Unit tests for backup directory configuration, retention policy pruning,
and automated scheduler [REQ-404-001, REQ-404-002, REQ-404-003, REQ-404-004, REQ-404-005].
"""

import os
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.application.system.backup_scheduler import DataDirBackupScheduler
from src.infrastructure.data.backup import DataDirBackupService
from src.infrastructure.data.resolver import (
    BACKUP_RETENTION_SETTING_KEY,
    BACKUP_SCHEDULE_SETTING_KEY,
    ENV_BACKUP_DIR,
    DataDirPaths,
    DataDirResolver,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _make_paths(root: Path, backups_path: Path | None = None) -> DataDirPaths:
    root.mkdir(parents=True, exist_ok=True)
    bpath = backups_path or root / "backups"
    bpath.mkdir(parents=True, exist_ok=True)
    return DataDirPaths(
        root=root,
        db_path=root / "database" / "autoreiv.db",
        wiki_path=root / "wiki",
        skills_path=root / "skills",
        agents_path=root / "agents",
        job_templates_path=root / "templates" / "jobs",
        packs_path=root / "packs",
        backups_path=bpath,
    )


def _seed_live_data(root: Path) -> None:
    db_file = root / "database" / "autoreiv.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE IF NOT EXISTS sample_data (content TEXT)")
    conn.execute("INSERT INTO sample_data VALUES ('mission-critical')")
    conn.commit()
    conn.close()

    wiki = root / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "system.md").write_text("# AutoReiv System\nOperational state.", encoding="utf-8")


def test_resolver_custom_backup_dir_resolution(tmp_path, monkeypatch):
    custom_bdir = tmp_path / "external_backups"
    monkeypatch.setenv(ENV_BACKUP_DIR, str(custom_bdir))

    resolver = DataDirResolver(
        home=tmp_path / "home",
        local_appdata=tmp_path / "appdata",
        checkout_root=tmp_path / "checkout",
    )
    paths = resolver.resolve()
    assert paths.backups_path == custom_bdir

    resolver.ensure_layout(paths)
    assert custom_bdir.is_dir()


def test_backup_service_resolve_backup_dir_precedence(tmp_path):
    root = tmp_path / "data"
    default_bdir = root / "backups"
    paths = _make_paths(root, backups_path=default_bdir)
    service = DataDirBackupService(paths)

    # 1. Default uses paths.backups_path
    assert service.resolve_backup_dir() == default_bdir

    # 2. Explicit custom dir overrides paths.backups_path
    override_bdir = tmp_path / "override_backups"
    assert service.resolve_backup_dir(override_bdir) == override_bdir


def test_backup_creation_in_custom_directory_and_no_self_nesting(tmp_path):
    root = tmp_path / "data"
    custom_bdir = root / "nested_backups"  # Inside root, to verify self-nesting protection
    _seed_live_data(root)

    paths = _make_paths(root, backups_path=custom_bdir)
    service = DataDirBackupService(paths)

    # First backup
    b1 = service.backup(backup_dir=custom_bdir)
    assert b1.parent == custom_bdir
    assert b1.exists()

    # Second backup should NOT contain the first backup
    b2 = service.backup(backup_dir=custom_bdir)
    assert b2.exists()

    with zipfile.ZipFile(b2) as zf:
        namelist = zf.namelist()
        assert not any("nested_backups" in n for n in namelist)
        assert not any("autoreiv-data-" in n for n in namelist)
        assert "database/autoreiv.db" in namelist
        assert "wiki/system.md" in namelist


def test_list_backups_metadata_and_ordering(tmp_path):
    root = tmp_path / "data"
    bdir = tmp_path / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    paths = _make_paths(root, backups_path=bdir)
    service = DataDirBackupService(paths)

    # Create dummy archives with timestamped names
    f1 = bdir / "autoreiv-data-20260901T010000Z.zip"
    f2 = bdir / "autoreiv-data-20260902T020000Z.zip"
    f3 = bdir / "pre-restore-20260903T030000Z.zip"
    unrelated = bdir / "unrelated.txt"

    f1.write_bytes(b"x" * 1024)
    f2.write_bytes(b"x" * (2 * 1024 * 1024))
    f3.write_bytes(b"x" * 512)
    unrelated.write_text("hello", encoding="utf-8")

    backups = service.list_backups(bdir)
    assert len(backups) == 3
    filenames = [b["filename"] for b in backups]
    # Newest timestamp first
    assert filenames == [
        "pre-restore-20260903T030000Z.zip",
        "autoreiv-data-20260902T020000Z.zip",
        "autoreiv-data-20260901T010000Z.zip",
    ]

    # Verify metadata fields
    b2_meta = next(b for b in backups if b["filename"] == f2.name)
    assert b2_meta["size_mb"] == 2.0
    assert b2_meta["is_pre_restore"] is False
    assert b2_meta["created_at"] == "2026-09-02T02:00:00Z"

    pre_meta = next(b for b in backups if b["filename"] == f3.name)
    assert pre_meta["is_pre_restore"] is True


def test_prune_backups_retention_policy_and_negative_assertions(tmp_path):
    root = tmp_path / "data"
    bdir = tmp_path / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    _seed_live_data(root)
    paths = _make_paths(root, backups_path=bdir)
    service = DataDirBackupService(paths)

    # Create 5 historical backups with distinct mtimes
    archives = []
    base_time = 1700000000.0
    for i in range(5):
        p = bdir / f"autoreiv-data-2026090{i + 1}T000000Z.zip"
        p.write_bytes(b"dummy")
        os.utime(str(p), (base_time + i * 3600, base_time + i * 3600))
        archives.append(p)

    # Also add a pre-restore archive and a random file
    pre_restore = bdir / "pre-restore-20260901T000000Z.zip"
    pre_restore.write_bytes(b"safety")
    os.utime(str(pre_restore), (base_time - 1000, base_time - 1000))

    unrelated_file = bdir / "notes.txt"
    unrelated_file.write_text("keep this", encoding="utf-8")

    # Prune with retention count 2: should keep the 2 newest archives
    # Newest are archive 4 (index 4) and archive 3 (index 3)
    pruned = service.prune_backups(retention_count=2, backup_dir=bdir)
    assert len(pruned) == 3
    assert set(pruned) == {archives[0].name, archives[1].name, archives[2].name}

    # Verify retained archives exist
    assert archives[4].exists()
    assert archives[3].exists()
    assert not archives[0].exists()
    assert not archives[1].exists()
    assert not archives[2].exists()

    # NEGATIVE ASSERTIONS:
    # 1. Pre-restore archives MUST NEVER be deleted by retention pruning
    assert pre_restore.exists()
    # 2. Non-backup files in backup directory MUST NEVER be touched
    assert unrelated_file.exists()
    # 3. Live database files in data root MUST NEVER be touched
    assert (root / "database" / "autoreiv.db").is_file()

    # Pruning again when remaining count (2) <= retention_count (2) prunes nothing
    pruned_again = service.prune_backups(retention_count=2, backup_dir=bdir)
    assert pruned_again == []


def test_delete_backup_and_path_traversal_rejection(tmp_path):
    root = tmp_path / "data"
    bdir = tmp_path / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    paths = _make_paths(root, backups_path=bdir)
    service = DataDirBackupService(paths)

    target_zip = bdir / "autoreiv-data-20260921T120000Z.zip"
    target_zip.write_bytes(b"content")

    # Path traversal attempts must be rejected
    with pytest.raises(ValueError, match="Invalid backup filename|Path traversal"):
        service.delete_backup("../secret.zip", backup_dir=bdir)

    with pytest.raises(ValueError, match="Invalid backup filename|Path traversal"):
        service.delete_backup("sub/test.zip", backup_dir=bdir)

    # Valid delete succeeds
    assert service.delete_backup(target_zip.name, backup_dir=bdir) is True
    assert not target_zip.exists()

    # Deleting non-existent file returns False
    assert service.delete_backup("autoreiv-data-missing.zip", backup_dir=bdir) is False


def test_backup_scheduler_due_checks_and_cadence(tmp_path):
    root = tmp_path / "data"
    _seed_live_data(root)
    paths = _make_paths(root)

    db_path = str(root / "database" / "autoreiv.db")
    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    scheduler = DataDirBackupScheduler(paths=paths, store=store, interval_seconds=1.0)

    now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Disabled schedule: never due
    assert scheduler.is_backup_due("disabled", None, now) is False
    assert scheduler.is_backup_due("", None, now) is False

    # Active schedule with no prior run: due immediately
    assert scheduler.is_backup_due("hourly", None, now) is True
    assert scheduler.is_backup_due("daily", None, now) is True

    # Hourly: 30 minutes elapsed -> not due
    last_run_30m = (now - timedelta(minutes=30)).isoformat()
    assert scheduler.is_backup_due("hourly", last_run_30m, now) is False

    # Hourly: 65 minutes elapsed -> due
    last_run_65m = (now - timedelta(minutes=65)).isoformat()
    assert scheduler.is_backup_due("hourly", last_run_65m, now) is True

    # Daily: yesterday 10:00 -> due (day changed and >1h passed)
    yesterday = (now - timedelta(days=1)).isoformat()
    assert scheduler.is_backup_due("daily", yesterday, now) is True


@pytest.mark.asyncio
async def test_backup_scheduler_tick_creates_and_prunes(tmp_path):
    root = tmp_path / "data"
    _seed_live_data(root)
    bdir = tmp_path / "custom_backups"
    bdir.mkdir(parents=True, exist_ok=True)
    paths = _make_paths(root, backups_path=bdir)

    db_path = str(root / "database" / "autoreiv.db")
    store = SQLiteStateStore(db_path=db_path)
    store.initialize_db()

    # Configure store settings
    store.set_setting(BACKUP_SCHEDULE_SETTING_KEY, "daily")
    store.set_setting(BACKUP_RETENTION_SETTING_KEY, 1)

    scheduler = DataDirBackupScheduler(paths=paths, store=store)

    # First tick: no last_backup_time, so backup is due and runs
    result1 = await scheduler.tick()
    assert result1 is not None
    assert result1["status"] == "created"
    assert (bdir / result1["filename"]).exists()

    last_time = store.get_setting("last_backup_time")
    assert last_time is not None

    # Immediate second tick at same time: not due
    result2 = await scheduler.tick()
    assert result2 is None

    # Tick 2 days in the future: due again, and prunes older archive (retention=1)
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    result3 = await scheduler.tick(now=future_time)
    assert result3 is not None
    assert result3["status"] == "created"
    assert result1["filename"] in result3["pruned"]
    assert not (bdir / result1["filename"]).exists()
    assert (bdir / result3["filename"]).exists()
