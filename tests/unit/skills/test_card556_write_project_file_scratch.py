r"""CARD-556 (D1, Jacob 2026-09-27): with no project selected, write_project_file writes to the AutoReiv
scratch folder under the user data folder (for example %LOCALAPPDATA%\AutoReiv\scratch). It never writes into the
AutoReiv checkout, and the tool result and description tell the model where the file went.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.sdlc.paths import autoreiv_checkout_roots, default_scratch_root
from src.application.sdlc.projects_service import ProjectsService
from src.application.skills.project_file_tools import ProjectFileTools
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

REPO = Path(__file__).resolve().parents[3]


def _inside(child: Path, parent: Path) -> bool:
    c, p = Path(child).resolve(), Path(parent).resolve()
    return c == p or p in c.parents


@pytest.fixture
def fake_checkout(tmp_path, monkeypatch) -> Path:
    co = tmp_path / "AutoReiv"
    (co / "docs" / "cards").mkdir(parents=True)
    (co / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    monkeypatch.chdir(co)
    monkeypatch.setenv("AUTOREIV_CHECKOUT_ROOT", str(co))
    return co


@pytest.fixture
def svc() -> ProjectsService:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    return ProjectsService(store=store)


def _tools(svc, scratch: Path) -> ProjectFileTools:
    return ProjectFileTools(root_resolver=svc.resolve_root, project_resolver=svc.selected_root, scratch_root=scratch)


def test_no_project_selected_writes_to_scratch_not_checkout(fake_checkout, svc, tmp_path):
    scratch = tmp_path / "data" / "scratch"
    res = _tools(svc, scratch).write_project_file("get_weather_tool.json", "{}")
    assert res["success"] is True, res
    assert Path(res["full_path"]) == (scratch / "get_weather_tool.json").resolve()
    assert (scratch / "get_weather_tool.json").read_text(encoding="utf-8") == "{}"
    assert not (fake_checkout / "get_weather_tool.json").exists()
    assert res["location"] == "scratch"
    assert res["project_root"] == str(scratch.resolve())


def test_result_tells_the_model_where_the_file_went(fake_checkout, svc, tmp_path):
    scratch = tmp_path / "data" / "scratch"
    res = _tools(svc, scratch).write_project_file("notes/a.txt", "hi")
    note = res["note"]
    assert str(scratch.resolve()) in note
    assert "no project is selected" in note.lower()
    assert "not" in note.lower() and "checkout" in note.lower()
    assert "repo_file_write" in note


def test_selected_project_still_wins(fake_checkout, svc, tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    svc.set_selected(slug="proj", path=str(proj))
    res = _tools(svc, tmp_path / "scratch").write_project_file("x.py", "x = 1\n")
    assert res["success"] is True and res["location"] == "project"
    assert (proj / "x.py").is_file()
    assert "note" not in res


def test_guard_never_resolves_into_the_checkout(fake_checkout, svc, tmp_path):
    """Guard: however the root is reached (explicit arg, selected project, sub-folder, absolute path), no write lands
    in the checkout."""
    tools = _tools(svc, tmp_path / "scratch")
    for kwargs in (
        {"path": "a.json", "project_root": str(fake_checkout)},
        {"path": "a.json", "project_root": str(fake_checkout / "docs")},
        {"path": str(fake_checkout / "a.json")},
    ):
        res = tools.write_project_file(content="{}", **kwargs)
        assert res["success"] is False, (kwargs, res)
    svc.set_selected(slug="AutoReiv", path=str(fake_checkout))
    res = tools.write_project_file("a.json", "{}")
    assert res["success"] is False and "repo_file_write" in res["error"]
    assert not any(p.name == "a.json" for p in fake_checkout.rglob("a.json"))


def test_guard_the_real_checkout_is_never_a_write_root(svc, tmp_path, monkeypatch):
    """With no configuration at all, the resolved write root is not inside this repository."""
    monkeypatch.chdir(REPO)
    monkeypatch.delenv("AUTOREIV_CHECKOUT_ROOT", raising=False)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    assert any(_inside(REPO, r) and _inside(r, REPO) for r in autoreiv_checkout_roots())
    for tools in (ProjectFileTools(), ProjectFileTools(root_resolver=svc.resolve_root, project_resolver=svc.selected_root)):
        res = tools.write_project_file("card556_probe.txt", "x")
        assert res["success"] is True, res
        assert not _inside(Path(res["full_path"]), REPO)
    assert not (REPO / "card556_probe.txt").exists()


def test_default_scratch_is_in_the_os_temp_folder(monkeypatch, tmp_path):
    """CARD-562: scratch lives in <OS temp>/autoreiv-scratch, outside every project and the data folder."""
    import tempfile

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))
    assert default_scratch_root() == (tmp_path / "tmp" / "autoreiv-scratch").resolve()


def test_selected_root_is_none_without_a_project(svc, tmp_path):
    assert svc.selected_root() is None
    assert svc.selected_root(str(tmp_path)) is None  # CARD-562: a passed root never replaces a selection
    svc.set_selected(slug="p", path=str(tmp_path))
    assert svc.selected_root() == tmp_path.resolve()


def test_description_names_scratch_and_checkout_tools(tmp_path):
    from src.application.kernel.tool_registry import ScopedToolRegistry

    reg = ScopedToolRegistry()
    ProjectFileTools(scratch_root=tmp_path / "scratch").register_tools(reg)
    desc = reg.get_tool_definition("write_project_file").description
    assert str((tmp_path / "scratch").resolve()) in desc
    assert "no project" in desc.lower() and "checkout" in desc.lower() and "repo_file_write" in desc


def test_bootstrap_scratch_is_the_os_temp_folder(tmp_path):
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    skills = tmp_path / "data" / "skills"
    skills.mkdir(parents=True)
    _, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=TelemetryCollector(store=store), skills_dir=str(skills))
    desc = tool_reg.get_tool_definition("write_project_file").description
    assert str(default_scratch_root()) in desc  # CARD-562: OS temp, not the data folder


def test_live_qa_scratch_under_a_protected_checkout_is_still_writable(tmp_path, monkeypatch):
    """Live QA keeps its throwaway data in <real checkout>/scratch/live_qa_data (gitignored) and protects the real
    checkout (CARD-555). The serve's own data root stays writable, so the no-project scratch works there; every other
    path under the protected checkout is still refused."""
    from src.application.sdlc.paths import PROTECTED_WRITE_ROOTS_ENV, protected_write_error

    real = tmp_path / "real"
    data = real / "scratch" / "live_qa_data"
    data.mkdir(parents=True)
    monkeypatch.setenv(PROTECTED_WRITE_ROOTS_ENV, str(real))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data))
    monkeypatch.delenv("AUTOREIV_CHECKOUT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert protected_write_error(data / "scratch" / "a.txt") is None
    assert protected_write_error(real / "a.txt")
    assert protected_write_error(real / "scratch" / "other.txt")
    res = ProjectFileTools().write_project_file("card556-note.txt", "hello 556")
    assert res["success"] is True, res
    assert Path(res["full_path"]) == default_scratch_root() / "card556-note.txt"  # CARD-562: OS temp
    assert not (real / "card556-note.txt").exists()
