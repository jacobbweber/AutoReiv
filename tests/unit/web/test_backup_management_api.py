"""
FastAPI integration tests for Backup Catalog and Management API
[REQ-404-001, REQ-404-002, REQ-404-003, REQ-404-004, REQ-404-005].
"""

import os
import sqlite3

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.data.resolver import (
    BACKUP_RETENTION_SETTING_KEY,
    BACKUP_SCHEDULE_SETTING_KEY,
    DataDirPaths,
    repo_root,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def _seed_db(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS notes (body TEXT)")
    conn.execute("INSERT INTO notes VALUES ('sample-backup-content')")
    conn.commit()
    conn.close()


@pytest.fixture
def app_with_custom_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "custom_data_dir"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "database" / "autoreiv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _seed_db(db_path)

    backups_dir = tmp_path / "custom_backups_dir"
    backups_dir.mkdir(parents=True, exist_ok=True)

    wiki_dir = data_dir / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "index.md").write_text("# Home\nWelcome to wiki.", encoding="utf-8")

    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    paths = DataDirPaths(
        root=data_dir,
        db_path=db_path,
        wiki_path=wiki_dir,
        skills_path=skills_dir,
        agents_path=data_dir / "agents",
        job_templates_path=data_dir / "templates" / "jobs",
        packs_path=data_dir / "packs",
        backups_path=backups_dir,
    )

    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    app = create_app(state_store=store, wiki_path=str(wiki_dir))
    app.state.data_dir_paths = paths
    app.state.store = store

    return app, paths, store


@pytest.mark.asyncio
async def test_get_and_run_backups_api(app_with_custom_data_dir):
    app, paths, store = app_with_custom_data_dir
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Initial list: should be empty
        res = await ac.get("/api/data-dir/backups")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert len(data["backups"]) == 0
        assert data["config"]["schedule"] == "disabled"
        assert data["config"]["retention_count"] == 7

        # 2. Trigger an immediate backup
        run_res = await ac.post("/api/data-dir/backups/run")
        assert run_res.status_code == 200
        created = run_res.json()
        assert created["status"] == "created"
        filename = created["filename"]
        assert filename.startswith("autoreiv-data-")
        assert filename.endswith(".zip")
        assert (paths.backups_path / filename).exists()

        # 3. List again: should contain the created archive
        res2 = await ac.get("/api/data-dir/backups")
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2["backups"]) == 1
        assert data2["backups"][0]["filename"] == filename

        # 4. Download the backup
        dl_res = await ac.get(f"/api/data-dir/backups/{filename}/download")
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/zip"
        assert len(dl_res.content) > 0


@pytest.mark.asyncio
async def test_delete_and_restore_backup_api(app_with_custom_data_dir):
    app, paths, store = app_with_custom_data_dir
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create a backup
        run_res = await ac.post("/api/data-dir/backups/run")
        filename = run_res.json()["filename"]

        # Restore without confirm=true fails with 400
        bad_restore = await ac.post(
            f"/api/data-dir/backups/{filename}/restore",
            json={"confirm": False},
        )
        assert bad_restore.status_code == 400

        # Valid restore succeeds
        ok_restore = await ac.post(
            f"/api/data-dir/backups/{filename}/restore",
            json={"confirm": True},
        )
        assert ok_restore.status_code == 200
        assert ok_restore.json()["status"] == "restored"

        # Delete backup
        del_res = await ac.delete(f"/api/data-dir/backups/{filename}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"
        assert not (paths.backups_path / filename).exists()

        # Delete again returns 404
        del_res2 = await ac.delete(f"/api/data-dir/backups/{filename}")
        assert del_res2.status_code == 404


@pytest.mark.asyncio
async def test_backup_config_get_and_put_api(app_with_custom_data_dir, tmp_path):
    app, paths, store = app_with_custom_data_dir
    orig_env = os.environ.get("AUTOREIV_BACKUP_DIR")
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Get config
            res = await ac.get("/api/data-dir/backup-config")
            assert res.status_code == 200
            cfg = res.json()
            assert cfg["schedule"] == "disabled"
            assert cfg["retention_count"] == 7

            # Updating with destination inside git checkout outside scratch/ is rejected [CARD-294]
            checkout = repo_root()
            forbidden_inside_repo = checkout / "src" / "forbidden_backups"
            bad_put = await ac.put(
                "/api/data-dir/backup-config",
                json={"backup_dir": str(forbidden_inside_repo)},
            )
            assert bad_put.status_code == 400
            assert "Refusing backup dir inside git checkout" in bad_put.json()["detail"]

            # Valid update
            new_backup_dir = tmp_path / "valid_new_backup_dir"
            put_res = await ac.put(
                "/api/data-dir/backup-config",
                json={
                    "schedule": "daily",
                    "retention_count": 14,
                    "backup_dir": str(new_backup_dir),
                },
            )
            assert put_res.status_code == 200
            updated = put_res.json()
            assert updated["status"] == "updated"
            assert updated["config"]["schedule"] == "daily"
            assert updated["config"]["retention_count"] == 14
            assert str(paths.backups_path) == str(new_backup_dir.resolve())
            assert store.get_setting(BACKUP_SCHEDULE_SETTING_KEY) == "daily"
            assert store.get_setting(BACKUP_RETENTION_SETTING_KEY) == 14
    finally:
        if orig_env is not None:
            os.environ["AUTOREIV_BACKUP_DIR"] = orig_env
        else:
            os.environ.pop("AUTOREIV_BACKUP_DIR", None)
