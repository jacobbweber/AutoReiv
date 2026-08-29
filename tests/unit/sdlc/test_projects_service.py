"""
Projects root jail, create, delete confirm [REQ-SDLC-050, REQ-SDLC-051].
"""

from pathlib import Path

from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.card_skill import CardSkill
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _svc(tmp_path: Path) -> ProjectsService:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    svc = ProjectsService(store=store, default_checkout=tmp_path / "checkout")
    (tmp_path / "checkout").mkdir()
    svc.set_projects_root(str(tmp_path / "lab"))
    (tmp_path / "lab").mkdir()
    return svc


def test_create_list_jail_and_delete_confirm(tmp_path: Path):
    svc = _svc(tmp_path)
    created = svc.create_project(slug="demo-app")
    assert created["success"] is True
    assert (tmp_path / "lab" / "demo-app").is_dir()
    listed = svc.list_projects()
    assert any(p["slug"] == "demo-app" for p in listed["projects"])
    escape = svc.create_project(slug="../outside")
    assert escape["success"] is False
    denied = svc.delete_project(slug="demo-app", confirm=False)
    assert denied["success"] is False
    assert "confirm" in denied["error"]
    assert (tmp_path / "lab" / "demo-app").is_dir()
    deleted = svc.delete_project(slug="demo-app", confirm=True)
    assert deleted["success"] is True
    assert not (tmp_path / "lab" / "demo-app").exists()


def test_selected_project_is_card_default_root(tmp_path: Path):
    svc = _svc(tmp_path)
    svc.create_project(slug="alpha")
    svc.set_selected(slug="alpha")
    skill = CardSkill(root_resolver=svc.resolve_root)
    (tmp_path / "lab" / "alpha" / ".github" / "cards").mkdir(parents=True)
    (tmp_path / "lab" / "alpha" / "AGENTS.md").write_text("# A\n", encoding="utf-8")
    listed = skill.list_cards()
    assert listed["success"] is True
    assert "alpha" in listed["project_root"]
