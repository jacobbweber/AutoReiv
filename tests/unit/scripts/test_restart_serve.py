# CARD-256 unit tests: restart_serve version parse + dry-run hygiene.
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "restart_serve.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("restart_serve", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["restart_serve"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rs():
    return _load_mod()


def test_parse_app_js_version_happy(rs):
    html = '<script type="module" src="/static/app.js?v=2.0.34"></script>'
    assert rs.parse_app_js_version(html) == "2.0.34"


def test_parse_app_js_version_missing(rs):
    assert rs.parse_app_js_version("<script src='/static/app.js'></script>") is None
    assert rs.parse_app_js_version("") is None


def test_index_html_keeps_versioned_cache_bust(rs):
    """REQ-SERVE-HYG-003: live index.html must keep app.js?v= pattern."""
    html = (ROOT / "src/web/templates/index.html").read_text(encoding="utf-8")
    ver = rs.parse_app_js_version(html)
    assert ver, "index.html must include /static/app.js?v=..."
    assert re_match_semverish(ver)


def re_match_semverish(ver: str) -> bool:
    import re

    return bool(re.fullmatch(r"[0-9]+(\.[0-9]+)*", ver))


def test_read_app_js_version_raises_when_missing(rs, tmp_path):
    (tmp_path / "src/web/templates").mkdir(parents=True)
    (tmp_path / "src/web/templates/index.html").write_text(
        "<html><script src='/static/app.js'></script></html>", encoding="utf-8"
    )
    with pytest.raises(ValueError, match=r"app\.js\?v="):
        rs.read_app_js_version(tmp_path)


def test_format_report_includes_tip_and_version(rs):
    text = rs.format_report(
        tip="abc123",
        branch="feat/control-plane-serve-hygiene-256",
        app_js_v="2.0.34",
        port=8000,
        host="127.0.0.1",
        orphans=[111],
        killed=[111],
        started=True,
        dry_run=True,
    )
    assert "tip_sha=abc123" in text
    assert "app.js?v=2.0.34" in text
    assert "port=8000" in text
    assert "dry_run=True" in text


def test_dry_run_does_not_kill_or_start(rs, tmp_path):
    """Dry-run must not call taskkill / start_serve side effects."""
    (tmp_path / "src/web/templates").mkdir(parents=True)
    (tmp_path / "src/web/templates/index.html").write_text(
        '<script type="module" src="/static/app.js?v=9.9.9"></script>',
        encoding="utf-8",
    )
    # minimal git repo for tip_sha
    import subprocess

    subprocess.check_call(["git", "init"], cwd=str(tmp_path), stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t"], cwd=str(tmp_path))
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=str(tmp_path))
    subprocess.check_call(["git", "add", "src"], cwd=str(tmp_path))
    subprocess.check_call(
        ["git", "commit", "-m", "t"],
        cwd=str(tmp_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with (
        patch.object(rs, "find_listener_pids", return_value=[4242]),
        patch.object(rs, "kill_pids", return_value=[4242]) as kill_mock,
        patch.object(rs, "start_serve", return_value=None) as start_mock,
    ):
        code = rs.main(["--dry-run", "--root", str(tmp_path), "--port", "8000"])
        assert code == 0
        kill_mock.assert_called()
        # dry_run=True must be passed
        assert kill_mock.call_args.kwargs.get("dry_run") is True
        start_mock.assert_not_called()


def test_status_is_non_mutating(rs, tmp_path, capsys):
    (tmp_path / "src/web/templates").mkdir(parents=True)
    (tmp_path / "src/web/templates/index.html").write_text(
        '<script type="module" src="/static/app.js?v=1.2.3"></script>',
        encoding="utf-8",
    )
    import subprocess

    subprocess.check_call(["git", "init"], cwd=str(tmp_path), stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "t@t"], cwd=str(tmp_path))
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=str(tmp_path))
    subprocess.check_call(["git", "add", "src"], cwd=str(tmp_path))
    subprocess.check_call(
        ["git", "commit", "-m", "t"],
        cwd=str(tmp_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with (
        patch.object(rs, "find_listener_pids", return_value=[7]),
        patch.object(rs, "kill_pids") as kill_mock,
        patch.object(rs, "start_serve") as start_mock,
    ):
        code = rs.main(["--status", "--root", str(tmp_path)])
        assert code == 0
        kill_mock.assert_not_called()
        start_mock.assert_not_called()
        out = capsys.readouterr().out
        assert "app.js?v=1.2.3" in out
        assert "orphans_found=[7]" in out
