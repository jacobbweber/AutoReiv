"""CARD-532: live QA environment (REQ-532-006/007/008, D1) - guards and data commands, no serve started."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import live_qa  # noqa: E402


def test_default_port_is_8770_and_port_8000_is_refused():
    assert live_qa.DEFAULT_PORT == 8770
    assert live_qa.validate_port(8770) == 8770
    with pytest.raises(ValueError, match="8000"):
        live_qa.validate_port(8000)


def test_default_data_dir_is_under_scratch_and_passes_the_live_data_guard(tmp_path):
    data_dir = live_qa.data_dir_for()
    assert data_dir == live_qa.CHECKOUT / "scratch" / "live_qa_data"
    env = {"LOCALAPPDATA": str(tmp_path / "local")}
    assert live_qa.data_problems(data_dir, env) == []


def test_data_dir_inside_live_appdata_is_refused(tmp_path):
    env = {"LOCALAPPDATA": str(tmp_path / "local")}
    live = tmp_path / "local" / "AutoReiv"
    assert live_qa.data_problems(live, env), "a data dir inside live AppData must be refused"


def _live_tree(root: Path) -> Path:
    (root / "database").mkdir(parents=True)
    (root / "wiki").mkdir()
    (root / "wiki" / "note.md").write_text("hello", encoding="utf-8")
    (root / ".vault_key").write_text("SECRET", encoding="utf-8")
    db = root / "database" / "autoreiv.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT)")
    conn.execute("INSERT INTO settings VALUES ('wiki_path', ?)", (json.dumps(str(root / "wiki")),))
    conn.execute("INSERT INTO settings VALUES ('provider_settings', '{}')")
    conn.commit()
    conn.close()
    return db


def test_clone_copies_real_data_without_the_vault_key_and_never_writes_back(tmp_path):
    src = tmp_path / "live" / "AutoReiv"
    db = _live_tree(src)
    before = {p: p.stat().st_mtime_ns for p in src.rglob("*") if p.is_file()}
    dst = tmp_path / "scratch" / "live_qa_data"
    info = live_qa.clone_appdata(src, dst)
    assert (dst / "wiki" / "note.md").read_text(encoding="utf-8") == "hello"
    assert not (dst / ".vault_key").exists()
    assert ".vault_key" in info["skipped"]
    assert {p: p.stat().st_mtime_ns for p in src.rglob("*") if p.is_file()} == before
    # The copy's wiki_path points into the copy; the source keeps its own.
    copy = sqlite3.connect(dst / "database" / "autoreiv.db")
    assert json.loads(copy.execute("SELECT value_json FROM settings WHERE key='wiki_path'").fetchone()[0]) == str(dst / "wiki")
    copy.close()
    orig = sqlite3.connect(db)
    assert json.loads(orig.execute("SELECT value_json FROM settings WHERE key='wiki_path'").fetchone()[0]) == str(src / "wiki")
    orig.close()
    assert "wiki_path" in info["repointed"]


def test_clone_refuses_overlapping_folders(tmp_path):
    src = tmp_path / "AutoReiv"
    _live_tree(src)
    with pytest.raises(ValueError):
        live_qa.clone_appdata(src, src / "inner")


def test_throwaway_env_gets_the_real_vllm_provider_with_env_overrides():
    body = live_qa.provider_payload({})
    assert body["provider_id"] == "vllm" and body["default_provider_id"] == "vllm"
    assert body["base_url"] == "http://192.168.1.218:8099/v1"
    assert body["default_model_id"] == "nemotron-3.5-lightning"
    other = live_qa.provider_payload({"AUTOREIV_QA_VLLM_URL": "http://x:1/v1", "AUTOREIV_QA_MODEL": "m"})
    assert other["base_url"] == "http://x:1/v1" and other["default_model_id"] == "m"


def test_runner_command_targets_the_qa_port_and_has_the_judge_off_by_default():
    cmd = live_qa.runner_command(8770, ["card-530"], ["desktop", "phone"])
    assert cmd[:2] == ["node", str(Path("tests") / "e2e" / "journeys" / "run.mjs")]
    assert "http://127.0.0.1:8770" in cmd and "--judge" not in cmd
    assert cmd[cmd.index("--journeys") + 1] == "card-530"
    assert cmd[cmd.index("--viewports") + 1] == "desktop,phone"
    assert "--judge" in live_qa.runner_command(8770, [], ["desktop"], judge=True)


def test_start_refuses_port_8000_before_touching_anything(tmp_path):
    with pytest.raises(ValueError):
        live_qa.start(8000, env={"LOCALAPPDATA": str(tmp_path)})
