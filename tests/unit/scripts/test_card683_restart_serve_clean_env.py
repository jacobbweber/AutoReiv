"""CARD-683: restart_serve never hands the calling shell's AUTOREIV_* variables to the serve it starts.

Live: a shell left with AUTOREIV_DATA_DIR / AUTOREIV_WIKI_PATH pointing at a throwaway folder restarted :8000, and
Jacob's serve came up on that folder. Now the serve gets the repo .env and explicit script parameters only, and
the script prints the data folder the serve will use.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "restart_serve.py"


@pytest.fixture(scope="module")
def rs():
    spec = importlib.util.spec_from_file_location("restart_serve_683", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["restart_serve_683"] = mod
    spec.loader.exec_module(mod)
    return mod


SHELL = {
    "PATH": "p",
    "AUTOREIV_DATA_DIR": r"C:\Temp\ar10\data679",
    "AUTOREIV_WIKI_PATH": r"C:\Temp\ar10\data679\wiki",
    "AUTOREIV_DB_PATH": r"C:\Temp\ar10\data679\database\autoreiv.db",
    "AUTOREIV_BACKUP_DIR": r"C:\Temp\ar10\data679\backups",
    "AUTOREIV_CHECKOUT_ROOT": r"C:\Temp\sandbox",
    "AUTOREIV_SERVE_PORT": "8770",
}


def test_shell_autoreiv_variables_are_not_passed_on(rs, tmp_path):
    env, dropped = rs.serve_child_env(SHELL, tmp_path)
    assert not [k for k in env if k.startswith("AUTOREIV_")]
    assert env["PATH"] == "p"
    assert set(dropped) == {k for k in SHELL if k.startswith("AUTOREIV_")}


def test_explicit_parameters_are_used(rs, tmp_path):
    env, _ = rs.serve_child_env(SHELL, tmp_path, data_dir=str(tmp_path / "d"), wiki_path=str(tmp_path / "w"),
                                db_path=str(tmp_path / "x.db"))
    assert env["AUTOREIV_DATA_DIR"] == str(tmp_path / "d")
    assert env["AUTOREIV_WIKI_PATH"] == str(tmp_path / "w")
    assert env["AUTOREIV_DB_PATH"] == str(tmp_path / "x.db")


def test_repo_env_file_is_the_configuration(rs, tmp_path):
    (tmp_path / ".env").write_text('AUTOREIV_DATA_DIR="D:\\AutoReivData"\nOTHER=1\n# AUTOREIV_WIKI_PATH=x\n', encoding="utf-8")
    env, _ = rs.serve_child_env({**SHELL, "OTHER": "shell"}, tmp_path)
    assert env["AUTOREIV_DATA_DIR"] == "D:\\AutoReivData"
    assert "AUTOREIV_WIKI_PATH" not in env
    assert env["OTHER"] == "shell"  # non-AutoReiv shell values still win, as before


def test_start_serve_does_not_pass_the_shell_data_folder(rs, tmp_path, monkeypatch):
    for k, v in SHELL.items():
        monkeypatch.setenv(k, v)
    seen = {}

    def fake_popen(cmd, **kwargs):
        seen["env"] = kwargs["env"]
        return object()

    with patch("subprocess.Popen", side_effect=fake_popen):
        rs.start_serve(tmp_path, host="0.0.0.0", port=8000, dry_run=False, log_path=tmp_path / "s.log")
    assert "AUTOREIV_DATA_DIR" not in seen["env"]
    assert "AUTOREIV_WIKI_PATH" not in seen["env"]


def test_data_folder_is_resolved_from_the_child_env(rs, tmp_path):
    env = {"AUTOREIV_DATA_DIR": str(tmp_path / "live")}
    paths = rs.resolve_data_paths(env, ROOT)
    assert Path(paths["data_dir"]) == tmp_path / "live"
    assert Path(paths["wiki"]) == tmp_path / "live" / "wiki"


def test_report_prints_the_data_folder(rs):
    text = rs.format_report(tip="abc", branch="qa", app_js_v="1", port=8000, host="0.0.0.0", orphans=[], killed=[],
                            started=True, dry_run=True, data={"data_dir": "C:\\Users\\j\\AppData\\Local\\AutoReiv",
                                                              "db": "x.db", "wiki": "w"},
                            dropped=["AUTOREIV_DATA_DIR"])
    assert "data_dir=C:\\Users\\j\\AppData\\Local\\AutoReiv" in text
    assert "ignored_shell_env=['AUTOREIV_DATA_DIR']" in text


def test_dry_run_prints_the_data_folder_without_the_shell_override(rs, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "throwaway"))
    with patch.object(rs, "find_listener_pids", return_value=[]), patch.object(rs, "tip_sha", return_value="abc"), \
            patch.object(rs, "tip_branch", return_value="qa"):
        assert rs.main(["--dry-run", "--root", str(ROOT), "--data-dir", str(tmp_path / "chosen")]) == 0
    out = capsys.readouterr().out
    assert f"data_dir={tmp_path / 'chosen'}" in out
    assert "throwaway" not in out.split("ignored_shell_env")[0]


def test_ps1_wrapper_forwards_explicit_data_parameters():
    ps1 = (ROOT / "scripts" / "restart_serve.ps1").read_text(encoding="utf-8")
    for flag in ("--data-dir", "--wiki-path", "--db-path"):
        assert flag in ps1


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_in_app_restart_keeps_the_serve_on_its_own_data_folder(platform, tmp_path, monkeypatch):
    """The serve itself restarting after an update passes its own data folder explicitly (a service's
    AUTOREIV_DATA_DIR must survive, now that restart_serve ignores inherited AUTOREIV_* variables)."""
    from src.application.system import serve_restarter

    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "restart_serve.ps1").write_text("", encoding="utf-8")
    monkeypatch.setenv("AUTOREIV_DATA_DIR", "/var/lib/autoreiv")
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", "/var/lib/autoreiv/wiki")
    monkeypatch.delenv("AUTOREIV_DB_PATH", raising=False)
    monkeypatch.setattr(serve_restarter.sys, "platform", platform)
    monkeypatch.setattr(serve_restarter.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(serve_restarter.subprocess, "DETACHED_PROCESS", 0x8, raising=False)
    seen = {}

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        return object()

    monkeypatch.setattr(serve_restarter.subprocess, "Popen", fake_popen)
    assert serve_restarter.DetachedScriptRestarter().schedule_restart(host="0.0.0.0", port=8000, repo_root=tmp_path)
    cmd = seen["cmd"]
    flag_dir, flag_wiki, flag_db = ("-DataDir", "-WikiPath", "-DbPath") if platform == "win32" else (
        "--data-dir", "--wiki-path", "--db-path")
    assert cmd[cmd.index(flag_dir) + 1] == "/var/lib/autoreiv"
    assert cmd[cmd.index(flag_wiki) + 1] == "/var/lib/autoreiv/wiki"
    assert flag_db not in cmd
