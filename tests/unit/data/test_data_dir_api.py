"""App wiring for the resolved data dir [REQ-DATA-001, REQ-DATA-002, REQ-DATA-005]."""

from fastapi.testclient import TestClient

from src.web.app import create_app


def test_create_app_exposes_data_dir_paths_and_api():
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/data-dir")
    assert res.status_code == 200
    data = res.json()
    assert data["root"]
    assert data["db_path"].endswith("autoreiv.db") or "test_isolated_autoreiv.db" in data["db_path"]
    assert "wiki" in data["wiki_path"]
    assert data["skills_path"].endswith("skills") or "skills" in data["skills_path"]
    assert app.state.wiki_path == data["wiki_path"]


def test_settings_html_shows_data_directory_panel():
    app = create_app()
    client = TestClient(app)
    html = client.get("/").text
    assert "dataDirRoot" in html
    assert "Data directory" in html
    assert "Hermes" not in html
    assert "backupDataDirBtn" in html
    assert "restoreDataDirBtn" in html
    assert "Backup data dir" in html


def _seed_data_dir_tree():
    import os
    import sqlite3
    from pathlib import Path

    root = Path(os.environ["AUTOREIV_DATA_DIR"])
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / "autoreiv.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS notes (body TEXT)")
    conn.execute("DELETE FROM notes")
    conn.execute("INSERT INTO notes VALUES ('api-v1')")
    conn.commit()
    conn.close()
    wiki = root / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "inbox.md").write_text("wiki-api-v1", encoding="utf-8")
    pack = root / "skills" / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "SKILL.md").write_text("# api-v1\n", encoding="utf-8")
    return root


def test_backup_api_returns_zip_with_tree(monkeypatch, tmp_path):
    import io
    import zipfile

    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    root = _seed_data_dir_tree()

    app = create_app()
    client = TestClient(app)
    res = client.post("/api/data-dir/backup")
    assert res.status_code == 200
    assert "zip" in res.headers.get("content-type", "")
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        names = set(zf.namelist())
    assert ("database/autoreiv.db" in names) or ("autoreiv.db" in names)
    assert "wiki/inbox.md" in names
    assert "skills/pack/SKILL.md" in names
    assert (root / "backups").is_dir()


def test_restore_api_requires_confirm_and_round_trips(monkeypatch, tmp_path):
    import io
    import sqlite3
    import zipfile

    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.delenv("AUTOREIV_WIKI_PATH", raising=False)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    root = _seed_data_dir_tree()

    app = create_app()
    client = TestClient(app)
    backup = client.post("/api/data-dir/backup")
    assert backup.status_code == 200
    zip_bytes = backup.content

    (root / "wiki" / "inbox.md").write_text("changed", encoding="utf-8")
    (root / "wiki" / "extra.md").write_text("gone", encoding="utf-8")

    refused = client.post(
        "/api/data-dir/restore",
        data={"confirm": "false"},
        files={"archive": ("backup.zip", zip_bytes, "application/zip")},
    )
    assert refused.status_code == 400
    assert (root / "wiki" / "inbox.md").read_text(encoding="utf-8") == "changed"

    restored = client.post(
        "/api/data-dir/restore",
        data={"confirm": "true"},
        files={"archive": ("backup.zip", zip_bytes, "application/zip")},
    )
    assert restored.status_code == 200
    body = restored.json()
    assert body["status"] == "restored"
    assert (root / "wiki" / "inbox.md").read_text(encoding="utf-8") == "wiki-api-v1"
    assert not (root / "wiki" / "extra.md").exists()
    db_file = root / "database" / "autoreiv.db" if (root / "database" / "autoreiv.db").is_file() else root / "autoreiv.db"
    conn = sqlite3.connect(str(db_file))
    assert conn.execute("SELECT body FROM notes").fetchone()[0] == "api-v1"
    conn.close()

    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as zf:
        zf.writestr("wiki/only.md", "no-db")
    rejected = client.post(
        "/api/data-dir/restore",
        data={"confirm": "true"},
        files={"archive": ("bad.zip", empty.getvalue(), "application/zip")},
    )
    assert rejected.status_code == 400
    assert (root / "wiki" / "inbox.md").read_text(encoding="utf-8") == "wiki-api-v1"
