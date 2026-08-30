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
