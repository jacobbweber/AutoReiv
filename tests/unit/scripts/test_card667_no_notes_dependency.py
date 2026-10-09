"""CARD-667: preflight and tests must not depend on the gitignored notes/ folder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".agents" / "skills" / "preflight" / "scripts" / "honesty_smoke_skill_261.py"


def _load_smoke():
    spec = importlib.util.spec_from_file_location("card667_honesty_smoke", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_artifact_path_uses_scratch_when_notes_absent(tmp_path):
    smoke = _load_smoke()
    out = smoke.artifact_path("honesty-smoke-261-fixtures.json", root=tmp_path)
    assert out == tmp_path / "scratch" / "honesty-smoke-261-fixtures.json"
    assert out.parent.is_dir()
    assert not (tmp_path / "notes").exists()


def test_artifact_path_keeps_notes_when_present(tmp_path):
    smoke = _load_smoke()
    (tmp_path / "notes").mkdir()
    out = smoke.artifact_path("marathon-card261-live-smoke.json", root=tmp_path)
    assert out == tmp_path / "notes" / "marathon-card261-live-smoke.json"


def test_validate_runs_green_without_notes(tmp_path, monkeypatch):
    smoke = _load_smoke()
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    payload = smoke.run_validate()
    assert payload["ok"] is True
    written = tmp_path / "scratch" / "honesty-smoke-261-fixtures.json"
    assert json.loads(written.read_text(encoding="utf-8"))["card"] == "CARD-261"
    assert not (tmp_path / "notes").exists()
