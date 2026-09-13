"""CARD-300: folder-only browse under projects_root."""

from pathlib import Path

from src.application.sdlc.projects_service import ProjectsService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _svc(tmp_path: Path) -> ProjectsService:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    svc = ProjectsService(store=store, default_checkout=tmp_path)
    (tmp_path / "Active").mkdir()
    (tmp_path / "Active" / "AppOne").mkdir()
    (tmp_path / "Active" / "readme.txt").write_text("x", encoding="utf-8")
    (tmp_path / "scratch").mkdir()
    svc.set_projects_root(str(tmp_path))
    return svc


def test_browse_folders_root_is_folder_only(tmp_path: Path):
    svc = _svc(tmp_path)
    data = svc.browse_folders(".")
    assert data["success"] is True
    names = {f["name"] for f in data["folders"]}
    assert names == {"Active", "scratch"}
    assert data["parent"] is None
    assert data["cwd"] == "."


def test_browse_folders_nested_and_up(tmp_path: Path):
    svc = _svc(tmp_path)
    data = svc.browse_folders("Active")
    assert data["success"] is True
    assert {f["name"] for f in data["folders"]} == {"AppOne"}
    assert data["parent"] == "."
    assert data["cwd"] == "Active"


def test_browse_folders_rejects_escape(tmp_path: Path):
    svc = _svc(tmp_path)
    data = svc.browse_folders("../outside")
    assert data["success"] is False
