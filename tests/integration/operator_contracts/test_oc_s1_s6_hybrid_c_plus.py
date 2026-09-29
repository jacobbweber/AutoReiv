"""OC-S1..S6: Hybrid C+ durable runtime registry [CARD-414 / ADR-0056].

Temp user-data only — never live %LOCALAPPDATA%\\AutoReiv.
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest


def _refuse_live(user_data: Path) -> None:
    local_app = os.environ.get("LOCALAPPDATA") or ""
    if not local_app:
        return
    live_root = (Path(local_app) / "AutoReiv").resolve()
    ud = str(user_data.resolve()).replace("\\", "/").lower()
    live = str(live_root).replace("\\", "/").lower()
    assert ud != live and not ud.startswith(live + "/"), (
        f"operator contracts must not use live user-data: {user_data}"
    )


@pytest.fixture
def hybrid_env(tmp_path, monkeypatch):
    """Isolated data root with explicit wiki (local mode)."""
    user_data = (tmp_path / "user-data").resolve()
    wiki = (tmp_path / "wiki-vault").resolve()
    user_data.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)
    _refuse_live(user_data)

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(user_data / "database" / "autoreiv.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")

    from starlette.testclient import TestClient

    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    (user_data / "database").mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=str(user_data / "database" / "autoreiv.db"))
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(wiki))
    client = TestClient(app)
    yield client, store, user_data, wiki
    client.close()




def test_oc_s3_backup_manifest_restore(hybrid_env, tmp_path):
    """OC-S3: backup/restore restores DB(s), wiki URI/policy, manifest."""
    from src.infrastructure.data.backup import MANIFEST_NAME, DataDirBackupService
    from src.infrastructure.data.resolver import DataDirPaths

    client, store, user_data, wiki = hybrid_env
    store.set_setting("oc_s3_probe", "hybrid-c-plus")
    paths = DataDirPaths(
        root=user_data,
        db_path=user_data / "database" / "autoreiv.db",
        wiki_path=wiki,
        skills_path=user_data / "skills",
        agents_path=user_data / "agents",
        job_templates_path=user_data / "templates" / "jobs",
        backups_path=user_data / "backups",
    )
    svc = DataDirBackupService(paths)
    dest = tmp_path / "backup.zip"
    out = svc.backup(dest)
    assert out.is_file()
    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
        assert MANIFEST_NAME in names, "OC-S3 FAIL: backup-manifest.json missing"
        manifest = json.loads(zf.read(MANIFEST_NAME))
    assert manifest.get("kind") == "autoreiv-backup-manifest"
    assert (manifest.get("wiki") or {}).get("uri")
    assert manifest.get("operational_db")

    # Restore into a fresh tree
    restore_root = tmp_path / "restore-root"
    restore_root.mkdir()
    restore_paths = DataDirPaths(
        root=restore_root,
        db_path=restore_root / "database" / "autoreiv.db",
        wiki_path=restore_root / "wiki",
        skills_path=restore_root / "skills",
        agents_path=restore_root / "agents",
        job_templates_path=restore_root / "templates" / "jobs",
        backups_path=restore_root / "backups",
    )
    DataDirBackupService(restore_paths).restore(out, confirm=True)
    assert restore_paths.db_path.is_file()
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    restored = SQLiteStateStore(db_path=str(restore_paths.db_path))
    restored.initialize_db()
    assert restored.get_setting("oc_s3_probe") == "hybrid-c-plus"




def test_oc_s5_wiki_path_persist_fail_visible(hybrid_env, tmp_path, monkeypatch):
    """OC-S5: configured wiki path persists; missing path fail-visible; migrate+rollback."""
    client, store, user_data, wiki = hybrid_env
    new_wiki = tmp_path / "relocated-wiki"
    # Persist via API
    res = client.put(
        "/api/settings/wiki-path",
        json={"path": str(new_wiki), "confirm_scaffold": True},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("wiki_path") == str(new_wiki)
    assert store.get_setting("wiki_path") == str(new_wiki)

    got = client.get("/api/settings/wiki-path")
    assert got.status_code == 200
    assert got.json().get("wiki_path") == str(new_wiki)

    # Missing path → fail-visible status (not silent alternate vault)
    missing = tmp_path / "does-not-exist-wiki"
    res2 = client.put(
        "/api/settings/wiki-path",
        json={"path": str(missing), "confirm_scaffold": False},
    )
    assert res2.status_code == 200
    st = client.get("/api/settings/wiki-path").json()
    assert st.get("wiki_status") in ("missing", "unreadable", "configured")
    # Rollback to previous wiki
    res3 = client.put(
        "/api/settings/wiki-path",
        json={"path": str(new_wiki), "confirm_scaffold": False},
    )
    assert res3.status_code == 200
    assert client.get("/api/settings/wiki-path").json().get("wiki_path") == str(new_wiki)


def test_oc_s6_local_gate_and_docker_hard_fail(tmp_path, monkeypatch):
    """OC-S6: local may auto-adopt data_root/wiki; Docker hard-fails if wiki missing; no second vault."""
    from src.infrastructure.data.resolver import DataDirResolver
    from src.infrastructure.data.wiki_gate import (
        WikiPathConfigurationError,
        enforce_wiki_path_for_boot,
    )

    user_data = (tmp_path / "ud").resolve()
    user_data.mkdir()
    _refuse_live(user_data)

    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))

    status = enforce_wiki_path_for_boot()
    assert status.status == "unset"
    # ensure_layout without scaffold must not mkdir wiki
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    resolver = DataDirResolver(in_docker=False)
    paths = resolver.resolve()
    assert paths.wiki_path == user_data / "wiki"
    wiki_before = paths.wiki_path.exists()
    resolver.ensure_layout(paths, scaffold_wiki=False)
    assert not paths.wiki_path.exists() or wiki_before
    # Must never invent a second vault name
    assert not (user_data / "wiki-vault").exists()

    # Local create_app with unset wiki auto-adopts data_root/wiki (single folder)
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore
    from src.web.app import create_app

    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "local")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))
    db = user_data / "database" / "autoreiv.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteStateStore(db_path=str(db))
    store.initialize_db()
    # Clear any prior wiki_path from store
    try:
        store.set_setting("wiki_path", "")
    except Exception:
        pass
    app = create_app(state_store=store)
    adopted = user_data / "wiki"
    assert Path(app.state.wiki_path).resolve() == adopted.resolve()
    assert adopted.is_dir()
    assert not (user_data / "wiki-vault").exists()
    persisted = store.get_setting("wiki_path")
    assert persisted and Path(str(persisted)).resolve() == adopted.resolve()

    # Docker hard-fail
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "docker")
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    with pytest.raises(WikiPathConfigurationError):
        enforce_wiki_path_for_boot()

    # Docker with valid path succeeds
    wiki = tmp_path / "docker-wiki"
    wiki.mkdir()
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki))
    ok = enforce_wiki_path_for_boot()
    assert ok.status == "configured"

    # create_app hard-fail path: isolated data root so peek cannot inherit local wiki_path
    docker_ud = (tmp_path / "docker-ud").resolve()
    docker_ud.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(docker_ud))
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "docker")
    db2 = docker_ud / "database" / "docker_fail.db"
    # AUTOREIV_DB_PATH must follow the docker root too: the resolver peeks wiki_path from it, and the
    # first `import src.web.app` (module-level create_app) persists a local wiki_path into the DB it
    # names. Under xdist that import can happen in this test, so the peek found the local wiki.
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db2))
    db2.parent.mkdir(parents=True, exist_ok=True)
    store2 = SQLiteStateStore(db_path=str(db2))
    store2.initialize_db()
    with pytest.raises(WikiPathConfigurationError):
        create_app(state_store=store2)

