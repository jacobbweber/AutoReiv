"""
Projects studio API [REQ-SDLC-050, REQ-SDLC-051].
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client(tmp_path: Path):
    store = SQLiteStateStore(db_path=str(tmp_path / "p.db"))
    store.initialize_db()
    app = create_app(state_store=store)
    with TestClient(app) as c:
        yield c, tmp_path


def test_projects_root_and_crud_jail(client):
    c, tmp_path = client
    lab = tmp_path / "lab"
    lab.mkdir()
    root_get = c.get("/api/settings/projects_root")
    assert root_get.status_code == 200
    assert root_get.json()["projects_root"] == ""
    assert "placeholder" in root_get.json()
    saved = c.put("/api/settings/projects_root", json={"path": str(lab)})
    assert saved.status_code == 200
    created = c.post("/api/projects", json={"slug": "demo-app"})
    assert created.status_code == 200
    assert (lab / "demo-app").is_dir()
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
