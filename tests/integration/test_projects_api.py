"""
Projects studio API [REQ-SDLC-050, REQ-SDLC-051, CARD-728, CARD-729].
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(tmp_path / "lab"))
    store = SQLiteStateStore(db_path=str(tmp_path / "p.db"))
    store.initialize_db()
    app = create_app(state_store=store)
    with TestClient(app) as c:
        yield c, tmp_path


def test_projects_folder_and_crud_jail(client):
    c, tmp_path = client
    lab = tmp_path / "lab"
    # CARD-728: the folder comes from AUTOREIV_PROJECTS_DIR / <data>/projects; there is no settings endpoint.
    assert c.get("/api/settings/projects_root").status_code in (404, 405)
    assert c.put("/api/settings/projects_root", json={"path": str(tmp_path)}).status_code in (404, 405)
    assert Path(c.get("/api/projects").json()["projects_root"]) == lab.resolve()
    created = c.post("/api/projects", json={"slug": "demo-app"})
    assert created.status_code == 200
    assert (lab / "demo-app").is_dir()
    # CARD-729: an empty git repo, no AutoReiv template files.
    assert not (lab / "demo-app" / "AGENTS.md").exists()
    assert not (lab / "demo-app" / ".agents").exists()
    escaped = c.post("/api/projects", json={"slug": "../nope"})
    assert escaped.status_code == 400
    listed = c.get("/api/projects")
    assert any(p["slug"] == "demo-app" for p in listed.json()["projects"])
    no_confirm = c.delete("/api/projects/demo-app")
    assert no_confirm.status_code == 400
    assert (lab / "demo-app").is_dir()
    deleted = c.delete("/api/projects/demo-app?confirm=true")
    assert deleted.status_code == 200
    assert not (lab / "demo-app").exists()
    selected = c.put("/api/projects/selected", json={"slug": "missing"})
    assert selected.status_code == 404


def test_selection_outside_projects_folder_or_running_checkout_is_refused(client):
    from src.infrastructure.data.resolver import repo_root

    c, tmp_path = client
    outside = tmp_path / "outside"
    outside.mkdir()
    assert c.put("/api/projects/selected", json={"path": str(outside)}).status_code == 400
    assert c.put("/api/projects/selected", json={"path": str(repo_root())}).status_code == 400
    assert c.get("/api/projects/selected").json()["selected"] == {}
    c.post("/api/projects", json={"slug": "ok"})
    picked = c.put("/api/projects/selected", json={"slug": "ok"})
    assert picked.status_code == 200
    assert Path(c.get("/api/projects/selected").json()["selected"]["path"]) == (tmp_path / "lab" / "ok").resolve()


def test_drift_and_align_endpoints_are_gone(client):
    c, _ = client
    assert c.get("/api/projects/drift").status_code in (404, 405)
    assert c.post("/api/projects/align", json={}).status_code in (404, 405)


def test_projects_files_list_and_read_jailed(client):
    c, tmp_path = client
    lab = tmp_path / "lab"
    c.post("/api/projects", json={"slug": "demo-app"})
    c.put("/api/projects/selected", json={"slug": "demo-app"})

    project_dir = lab / "demo-app"
    (project_dir / "README.md").write_text("# Demo Project\nWelcome to demo.", encoding="utf-8")
    (project_dir / ".agents" / "cards").mkdir(parents=True, exist_ok=True)
    (project_dir / ".agents" / "cards" / "CARD-001.md").write_text("# CARD-001", encoding="utf-8")
    (project_dir / ".git").mkdir(parents=True, exist_ok=True)
    (project_dir / ".git" / "config").write_text("dummy", encoding="utf-8")

    # List root
    res = c.get("/api/projects/files/list")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["path"] == "."
    names = [e["name"] for e in data["entries"]]
    assert "README.md" in names
    assert ".agents" in names
    assert ".git" not in names  # Filtered out noise

    # List subfolder
    res_sub = c.get("/api/projects/files/list?path=.agents/cards")
    assert res_sub.status_code == 200
    sub_names = [e["name"] for e in res_sub.json()["entries"]]
    assert "CARD-001.md" in sub_names

    # Category filter
    res_cat = c.get("/api/projects/files/list?category=cards")
    assert res_cat.status_code == 200
    cat_names = [e["name"] for e in res_cat.json()["entries"]]
    assert "CARD-001.md" in cat_names

    # Read file
    res_read = c.get("/api/projects/files/read?path=README.md")
    assert res_read.status_code == 200
    read_data = res_read.json()
    assert read_data["success"] is True
    assert "# Demo Project" in read_data["content"]
    assert read_data["is_markdown"] is True

    # Traversal escape rejected
    res_escape_read = c.get("/api/projects/files/read?path=../../outside.txt")
    assert res_escape_read.status_code in (400, 403, 404)
    res_escape_list = c.get("/api/projects/files/list?path=../../")
    assert res_escape_list.status_code in (400, 403, 404)

