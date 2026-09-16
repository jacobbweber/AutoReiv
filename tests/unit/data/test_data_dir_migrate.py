"""CARD-313: POST /api/data-dir/migrate copies, validates, backup-renames, persists."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from src.infrastructure.data.migrate import (
    DataDirRelocateError,
    migrate_data_dir,
    persist_autoreiv_data_dir,
)
from src.web.app import create_app


def _seed_tree(root: Path) -> Path:
    """Minimal recognizable data tree (db under database/)."""
    root.mkdir(parents=True, exist_ok=True)
    db_dir = root / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_dir / "autoreiv.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS notes (body TEXT)")
    conn.execute("DELETE FROM notes")
    conn.execute("INSERT INTO notes VALUES ('migrate-v1')")
    conn.commit()
    conn.close()
    wiki = root / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "inbox.md").write_text("wiki-migrate-v1", encoding="utf-8")
    skills = root / "skills" / "pack"
    skills.mkdir(parents=True, exist_ok=True)
    (skills / "SKILL.md").write_text("# migrate\n", encoding="utf-8")
    return root


def test_migrate_data_dir_copies_validates_renames_and_persists(tmp_path, monkeypatch):
    checkout = tmp_path / "repo"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    source = tmp_path / "live-data"
    dest = tmp_path / "new-data"
    _seed_tree(source)

    monkeypatch.chdir(checkout)
    result = migrate_data_dir(source, dest, checkout=checkout)

    assert result.destination == dest.resolve()
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert not source.exists()
    assert (dest / "wiki" / "inbox.md").read_text(encoding="utf-8") == "wiki-migrate-v1"
    assert (dest / "database" / "autoreiv.db").is_file()
    assert os.environ.get("AUTOREIV_DATA_DIR") == str(dest.resolve())
    env_text = (checkout / ".env").read_text(encoding="utf-8")
    assert f"AUTOREIV_DATA_DIR={dest.resolve()}" in env_text
    conn = sqlite3.connect(str(dest / "database" / "autoreiv.db"))
    row = conn.execute("SELECT value_json FROM settings WHERE key='data_dir'").fetchone()
    conn.close()
    assert row is not None
    assert json.loads(row[0]) == str(dest.resolve())


def test_migrate_refuses_nonempty_destination(tmp_path):
    source = tmp_path / "src"
    dest = tmp_path / "dest"
    _seed_tree(source)
    dest.mkdir()
    (dest / "keep.txt").write_text("nope", encoding="utf-8")
    try:
        migrate_data_dir(source, dest, checkout=tmp_path / "repo")
        assert False, "expected DataDirRelocateError"
    except DataDirRelocateError as exc:
        assert "not empty" in str(exc).lower()
    assert source.exists()


def test_migrate_api_round_trip(monkeypatch, tmp_path):
    """API uses app-resolved root; patch migrate to write .env under a fake checkout."""
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    data = tmp_path / "data"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    # Let create_app bootstrap a real schema — only seed wiki/skills markers; no hand-rolled settings table.
    data.mkdir(parents=True, exist_ok=True)
    (data / "wiki").mkdir(parents=True, exist_ok=True)
    (data / "wiki" / "inbox.md").write_text("wiki-migrate-v1", encoding="utf-8")
    pack = data / "skills" / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "SKILL.md").write_text("# migrate\n", encoding="utf-8")

    app = create_app()
    client = TestClient(app)

    dest = tmp_path / "relocated"
    import src.infrastructure.data.migrate as migrate_mod
    import src.web.routers.data_dir_migrate as settings_router

    fake_checkout = tmp_path / "fake-checkout"
    fake_checkout.mkdir()
    (fake_checkout / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    real_migrate = migrate_mod.migrate_data_dir

    def _wrapped(source, destination, *, checkout=None):
        return real_migrate(source, destination, checkout=fake_checkout)

    monkeypatch.setattr(settings_router, "migrate_data_dir", _wrapped)

    res = client.post("/api/data-dir/migrate", json={"destination": str(dest)})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "migrated"
    assert Path(body["root"]).resolve() == dest.resolve()
    assert (dest / "wiki" / "inbox.md").is_file()
    again = client.get("/api/data-dir")
    assert again.status_code == 200
    assert Path(again.json()["root"]).resolve() == dest.resolve()


def test_persist_upserts_dotenv(tmp_path):
    checkout = tmp_path / "repo"
    checkout.mkdir()
    env = checkout / ".env"
    env.write_text("HOST=0.0.0.0\nAUTOREIV_DATA_DIR=/old\nPORT=8000\n", encoding="utf-8")
    dest = tmp_path / "x"
    dest.mkdir()
    (dest / "wiki").mkdir()
    vias = persist_autoreiv_data_dir(dest, checkout=checkout)
    assert any(v.startswith(".env:") for v in vias)
    text = env.read_text(encoding="utf-8")
    assert f"AUTOREIV_DATA_DIR={dest.resolve()}" in text
    assert text.count("AUTOREIV_DATA_DIR=") == 1
    assert "HOST=0.0.0.0" in text
