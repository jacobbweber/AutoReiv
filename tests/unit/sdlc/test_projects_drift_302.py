"""CARD-302: structure-only project template drift."""

from pathlib import Path

from src.application.sdlc.projects_service import ProjectsService
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_manifest_loaded_and_drift_detects_missing(tmp_path: Path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    svc = ProjectsService(store=store, default_checkout=tmp_path)
    proj = tmp_path / "demo"
    proj.mkdir()
    (proj / "README.md").write_text("x", encoding="utf-8")
    svc.set_selected(slug="demo", path=str(proj))

    drift = svc.detect_drift()
    assert drift["success"] is True
    assert drift["template_version"]
    assert "AGENTS.md" in drift["missing"]
    assert drift["aligned"] is False

    aligned = svc.align_project()
    assert aligned["success"] is True
    assert (proj / "AGENTS.md").exists()
    assert (proj / ".agents" / "steering" / "product.md").exists()
    again = svc.detect_drift()
    assert again["aligned"] is True
    assert again["missing"] == []


def test_require_selected_root_no_silent_autoreiv_fallback(tmp_path: Path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    svc = ProjectsService(store=store, default_checkout=tmp_path / "autoreiv-checkout")
    (tmp_path / "autoreiv-checkout").mkdir()
    try:
        svc.require_selected_root()
        assert False, "expected ProjectPathError"
    except Exception as exc:
        assert "No active project" in str(exc)
