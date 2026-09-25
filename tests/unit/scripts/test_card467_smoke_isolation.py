"""CARD-467: test runs must never touch live AppData (smoke server + pytest bootstrap)."""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "smoke_server.py"
PLAYWRIGHT_CONFIG = ROOT / "playwright.config.js"


def _load():
    spec = importlib.util.spec_from_file_location("smoke_server_card467", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["smoke_server_card467"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ss():
    return _load()


@pytest.fixture
def fake_live(tmp_path, monkeypatch):
    """A fake LOCALAPPDATA with a live-looking AutoReiv tree, exported like Jarvis's shell."""
    local = tmp_path / "LocalAppData"
    live = local / "AutoReiv"
    (live / "packs" / "developer").mkdir(parents=True)
    marker = live / "packs" / "developer" / "pack.json"
    marker.write_text('{"name": "Super Developer"}', encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(live))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(live / "database" / "autoreiv.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(live / "wiki"))
    return live, marker


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "checkout"
    (root / "scratch").mkdir(parents=True)
    return root


def _never_run(*_a, **_k):
    raise AssertionError("uvicorn must not start")


# --- REQ-467-001: playwright config uses the launcher, scratch paths, no reuse ---


def test_req_467_001_playwright_config_uses_launcher_and_scratch_paths():
    text = PLAYWRIGHT_CONFIG.read_text(encoding="utf-8")
    assert re.search(r"command:\s*'python scripts/smoke_server\.py", text)
    assert re.search(r"reuseExistingServer:\s*false", text)
    assert "uvicorn" not in re.search(r"command:\s*'([^']*)'", text).group(1)
    env_block = re.search(r"env:\s*\{([^}]*)\}", text).group(1)
    pairs = dict(re.findall(r"(AUTOREIV_[A-Z_]+):\s*'([^']*)'", env_block))
    assert set(pairs) == {"AUTOREIV_DATA_DIR", "AUTOREIV_DB_PATH", "AUTOREIV_WIKI_PATH"}
    for key, value in pairs.items():
        assert value.startswith("./scratch/smoke_data"), (key, value)


def test_req_467_001_smoke_env_ignores_parent_shell(ss, tmp_path):
    data_dir = tmp_path / "checkout" / "scratch" / "smoke_data"
    parent = {
        "AUTOREIV_DATA_DIR": r"C:\Users\jacob\AppData\Local\AutoReiv",
        "AUTOREIV_DB_PATH": r"C:\live\autoreiv.db",
        "AUTOREIV_WIKI_PATH": r"C:\live\wiki",
        "AUTOREIV_BACKUP_DIR": r"C:\live\backups",
        "LOCALAPPDATA": r"C:\Users\jacob\AppData\Local",
        "PATH": "keep-me",
    }
    env = ss.build_smoke_env(parent, data_dir)
    assert env["AUTOREIV_DATA_DIR"] == str(data_dir)
    assert env["AUTOREIV_DB_PATH"] == str(data_dir / "database" / "autoreiv.db")
    assert env["AUTOREIV_WIKI_PATH"] == str(data_dir / "wiki")
    assert env["AUTOREIV_BACKUP_DIR"] == str(data_dir / "backups")
    assert env["LOCALAPPDATA"] == str(data_dir / "_localappdata")
    assert env["PATH"] == "keep-me"
    assert parent["AUTOREIV_DATA_DIR"].endswith("AutoReiv")  # caller's mapping untouched


def test_req_467_001_check_only_with_live_env_resolves_scratch(ss, fake_live, checkout, capsys):
    live, marker = fake_live
    rc = ss.main(["--check-only"], checkout=checkout, runner=_never_run)
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK: all paths under scratch/" in out
    assert str(checkout / "scratch" / "smoke_data") in out
    assert str(live) not in out
    assert marker.read_text(encoding="utf-8") == '{"name": "Super Developer"}'


def test_req_467_001_serve_wipes_smoke_dir_then_runs_uvicorn_on_scratch(ss, fake_live, checkout):
    live, _ = fake_live
    data_dir = checkout / "scratch" / "smoke_data"
    (data_dir / "database").mkdir(parents=True)
    stale = data_dir / "database" / "autoreiv.db"
    stale.write_text("stale", encoding="utf-8")
    calls = []

    def runner(cmd, env, cwd):
        calls.append((cmd, env, cwd))
        assert not stale.exists(), "smoke dir must be wiped before uvicorn starts"
        return 0

    assert ss.main(["--port", "8765"], checkout=checkout, runner=runner) == 0
    (cmd, env, cwd) = calls[0]
    assert cmd[1:4] == ["-m", "uvicorn", "src.web.app:app"]
    assert cmd[-2:] == ["--port", "8765"]
    assert cwd == str(checkout)
    for key in ("AUTOREIV_DATA_DIR", "AUTOREIV_DB_PATH", "AUTOREIV_WIKI_PATH", "AUTOREIV_BACKUP_DIR", "LOCALAPPDATA"):
        assert ss.is_within(env[key], data_dir), key
        assert not ss.is_within(env[key], live), key


# --- REQ-467-002: guard refuses live AppData / platform default / repo-not-scratch ---


def test_req_467_002_guard_refuses_live_appdata_data_dir(ss, fake_live, checkout, capsys):
    live, marker = fake_live
    rc = ss.main(["--data-dir", str(live)], checkout=checkout, runner=_never_run)
    err = capsys.readouterr().err
    assert rc == ss.EXIT_REFUSED
    assert "REFUSED" in err and "inside live user data" in err
    assert marker.read_text(encoding="utf-8") == '{"name": "Super Developer"}'  # not wiped


def test_req_467_002_guard_refuses_repo_path_outside_scratch(ss, fake_live, checkout, capsys):
    rc = ss.main(["--check-only", "--data-dir", str(checkout / "data")], checkout=checkout, runner=_never_run)
    assert rc == ss.EXIT_REFUSED
    assert "outside" in capsys.readouterr().err


def test_req_467_002_live_data_problems_rules(ss, tmp_path):
    local = tmp_path / "Local"
    checkout = tmp_path / "repo"
    forbidden = ss.live_data_roots({"LOCALAPPDATA": str(local)}, home=tmp_path / "home")
    assert local / "AutoReiv" in forbidden
    scratch = checkout / "scratch"
    ok = {"root": scratch / "smoke_data", "db_path": scratch / "smoke_data" / "database" / "autoreiv.db"}
    assert ss.live_data_problems(ok, forbidden, required_parent=scratch) == []
    bad_default = {"packs_path": local / "AutoReiv" / "packs"}
    assert "inside live user data" in ss.live_data_problems(bad_default, forbidden, required_parent=scratch)[0]
    bad_home = {"root": tmp_path / "home" / ".autoreiv"}
    assert ss.live_data_problems(bad_home, forbidden)
    bad_repo = {"root": checkout / "data"}
    assert "outside" in ss.live_data_problems(bad_repo, forbidden, required_parent=scratch)[0]


def test_req_467_002_live_db_data_dir_setting_is_forbidden(ss, tmp_path):
    import json
    import sqlite3

    local = tmp_path / "Local"
    db = local / "AutoReiv" / "database" / "autoreiv.db"
    db.parent.mkdir(parents=True)
    moved = tmp_path / "MovedData"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value_json TEXT)")
    conn.execute("INSERT INTO settings VALUES ('data_dir', ?)", (json.dumps(str(moved)),))
    conn.commit()
    conn.close()
    forbidden = ss.live_data_roots({"LOCALAPPDATA": str(local)}, home=tmp_path / "home")
    assert moved in forbidden


def test_req_467_002_wipe_only_under_scratch(ss, checkout, tmp_path):
    with pytest.raises(ValueError):
        ss.wipe_smoke_dir(tmp_path / "elsewhere", checkout)
    with pytest.raises(ValueError):
        ss.wipe_smoke_dir(checkout / "scratch", checkout)
    target = checkout / "scratch" / "smoke_data"
    (target / "x").mkdir(parents=True)
    ss.wipe_smoke_dir(target, checkout)
    assert not target.exists()


# --- REQ-467-004: pytest forces temp paths and refuses live AppData ---


def test_req_467_004_pytest_env_overrides_preset_live_values(tmp_path):
    from tests.conftest import isolate_pytest_data_env

    env = {
        "AUTOREIV_DATA_DIR": r"C:\Users\jacob\AppData\Local\AutoReiv",
        "AUTOREIV_DB_PATH": r"C:\live\autoreiv.db",
        "AUTOREIV_WIKI_PATH": r"C:\live\wiki",
        "AUTOREIV_BACKUP_DIR": r"C:\live\backups",
    }
    base = isolate_pytest_data_env(env, base=tmp_path)
    assert env["AUTOREIV_DATA_DIR"] == str(base / "data")
    assert env["AUTOREIV_DB_PATH"] == str(base / "pytest_bootstrap.db")
    assert env["AUTOREIV_WIKI_PATH"] == str(base / "wiki")
    assert "AUTOREIV_BACKUP_DIR" not in env


def test_req_467_004_pytest_guard_flags_live_appdata(fake_live):
    from tests.conftest import live_appdata_problems

    problems = live_appdata_problems()
    assert problems and any("inside live user data" in p for p in problems)


def test_req_467_004_current_session_is_not_on_live_appdata():
    from tests.conftest import live_appdata_problems

    assert live_appdata_problems() == []
    real_live = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "AutoReiv"
    from src.web import app as app_module

    root = Path(app_module.app.state.data_dir_paths.root)
    assert real_live.resolve() not in [root.resolve(), *root.resolve().parents]
