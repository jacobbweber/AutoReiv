"""CARD-728 / CARD-729 / ADR-0067 guard: projects live in one user-data folder; process lives in skills.

Rules (ADR-0067):
1. One projects folder: `DataDirResolver().resolve().projects_path` (env AUTOREIV_PROJECTS_DIR, else <root>/projects).
   No `projects_root` setting or `/api/settings/projects_root` endpoint.
2. A selected project is inside that folder and never the running AutoReiv checkout.
3. No template push: no detect_drift / align_project tools or endpoints, no templates/sdlc-project.
4. Process lives in skills: repo-onboarding and spec-driven-development ship; software-development offers cli_exec.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.sdlc.projects_service import ProjectsService
from src.infrastructure.data.resolver import DataDirResolver, repo_root
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard

REPO = Path(__file__).resolve().parents[3]


def _store() -> SQLiteStateStore:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    return store


def test_projects_path_defaults_under_data_root_and_env_overrides(tmp_path, monkeypatch):
    monkeypatch.delenv("AUTOREIV_PROJECTS_DIR", raising=False)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    paths = DataDirResolver().resolve()
    assert paths.projects_path == tmp_path / "data" / "projects"

    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(tmp_path / "elsewhere"))
    assert DataDirResolver().resolve().projects_path == tmp_path / "elsewhere"


def test_projects_dir_inside_checkout_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(repo_root() / "src"))
    assert DataDirResolver().resolve().projects_path == tmp_path / "data" / "projects"


def test_service_uses_resolved_folder_and_has_no_projects_root_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(tmp_path / "projects"))
    svc = ProjectsService(store=_store())
    assert Path(svc.list_projects()["projects_root"]) == (tmp_path / "projects").resolve()
    assert not hasattr(svc, "set_projects_root")
    assert not hasattr(svc, "get_projects_root")


def test_selection_outside_folder_or_running_checkout_is_refused(tmp_path):
    folder = tmp_path / "projects"
    (folder / "demo").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    svc = ProjectsService(store=_store(), projects_dir=folder)

    assert svc.set_selected(path=str(outside))["success"] is False
    assert svc.set_selected(path=str(repo_root()))["success"] is False
    assert svc.get_selected() == {}
    assert svc.set_selected(slug="demo")["success"] is True
    assert Path(svc.get_selected()["path"]) == (folder / "demo").resolve()


def test_stored_selection_outside_folder_is_ignored(tmp_path):
    folder = tmp_path / "projects"
    folder.mkdir()
    store = _store()
    store.set_setting("selected_project", {"slug": "app", "path": str(repo_root())})
    svc = ProjectsService(store=store, projects_dir=folder)
    assert svc.get_selected() == {}
    assert svc.selected_root() is None


def test_running_checkout_cannot_be_selected_even_inside_folder(tmp_path):
    svc = ProjectsService(store=_store(), projects_dir=repo_root().parent)
    res = svc.set_selected(path=str(repo_root()))
    assert res["success"] is False
    assert "AutoReiv" in res["error"]


def test_no_projects_root_endpoint_and_no_drift_align_routes():
    from src.web.routers.projects import router

    paths = {getattr(r, "path", "") for r in router.routes}
    assert "/api/settings/projects_root" not in paths
    assert "/api/projects/drift" not in paths
    assert "/api/projects/align" not in paths


def test_no_template_push_tools_or_template_folder():
    from src.application.kernel.tool_registry import ScopedToolRegistry

    reg = ScopedToolRegistry()
    ProjectsService(store=_store()).register_tools(reg)
    names = {d.name for d in reg.list_tools()}
    assert "create_project" in names
    assert "detect_drift" not in names
    assert "align_project" not in names
    assert not (REPO / "templates" / "sdlc-project").exists()


def test_create_project_is_an_empty_git_repo(tmp_path):
    svc = ProjectsService(store=_store(), projects_dir=tmp_path / "projects")
    res = svc.create_project(slug="fresh")
    assert res["success"] is True
    target = Path(res["path"])
    assert sorted(p.name for p in target.iterdir()) in ([], [".git"])
    assert not (target / "AGENTS.md").exists()


def test_process_skills_ship_and_software_development_offers_cli_exec():
    from src.domain.frontmatter import split_frontmatter

    def tools_of(skill_id: str) -> list[str]:
        meta, _ = split_frontmatter((REPO / "platform" / "skills" / skill_id / "SKILL.md").read_text(encoding="utf-8"))
        return list(meta.get("tools") or [])

    assert "read_project_file" in tools_of("repo-onboarding")
    assert "write_project_file" in tools_of("spec-driven-development")
    assert "cli_exec" in tools_of("software-development")
    for retired in ("detect_drift", "align_project"):
        for skill in ("project-cards", "software-development", "repo-onboarding"):
            assert retired not in tools_of(skill)
