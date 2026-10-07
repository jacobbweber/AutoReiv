"""CARD-671: systemd installer/uninstaller take --prefix and --data-dir.

Script-level checks. Rendering runs bash with --print-unit / --dry-run, which need no root.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SYSTEMD = ROOT / "deploy" / "systemd"
INSTALL = SYSTEMD / "install_systemd.sh"
UNINSTALL = SYSTEMD / "uninstall_systemd.sh"
UNIT = SYSTEMD / "autoreiv.service"

needs_bash = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None, reason="needs a POSIX bash"
)


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args], capture_output=True, text=True, timeout=30, check=False
    )


def test_scripts_declare_prefix_and_data_dir_options():
    for script in (INSTALL, UNINSTALL):
        text = script.read_text(encoding="utf-8")
        assert "--prefix" in text and "--data-dir" in text, script.name
    assert "--purge-data" in UNINSTALL.read_text(encoding="utf-8")


def test_install_paths_only_appear_as_defaults():
    text = INSTALL.read_text(encoding="utf-8")
    assert text.count('"/opt/autoreiv"') == 1
    assert text.count('"/var/lib/autoreiv"') == 1
    un = UNINSTALL.read_text(encoding="utf-8")
    assert un.count('"/opt/autoreiv"') == 1
    assert un.count('"/var/lib/autoreiv"') == 1


@needs_bash
def test_print_unit_defaults_match_shipped_unit():
    res = _run(INSTALL, "--print-unit")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == UNIT.read_text(encoding="utf-8").strip()


@needs_bash
def test_print_unit_rewrites_prefix_and_data_dir():
    res = _run(INSTALL, "--prefix", "/srv/ar-test", "--data-dir", "/srv/ar-data", "--print-unit")
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert "WorkingDirectory=/srv/ar-test\n" in out
    assert "ExecStart=/srv/ar-test/.venv/bin/python -m src.cli.main serve" in out
    assert 'Environment="AUTOREIV_DATA_DIR=/srv/ar-data"' in out
    assert "ReadWritePaths=/srv/ar-data\n" in out
    assert "/opt/autoreiv" not in out and "/var/lib/autoreiv" not in out


@needs_bash
def test_install_rejects_relative_or_unknown_args():
    assert _run(INSTALL, "--data-dir", "rel/path", "--print-unit").returncode != 0
    assert _run(INSTALL, "--bogus").returncode != 0
    assert _run(INSTALL, "--help").returncode == 0


@needs_bash
def test_uninstall_dry_run_keeps_data_unless_purge():
    keep = _run(UNINSTALL, "--prefix", "/srv/ar-test", "--data-dir", "/srv/ar-data", "--dry-run")
    assert keep.returncode == 0, keep.stderr
    assert "remove /srv/ar-test" in keep.stdout
    assert "keep /srv/ar-data" in keep.stdout
    assert "remove /srv/ar-data" not in keep.stdout

    purge = _run(
        UNINSTALL, "--prefix", "/srv/ar-test", "--data-dir", "/srv/ar-data", "--purge-data", "--dry-run"
    )
    assert purge.returncode == 0, purge.stderr
    assert "remove /srv/ar-data" in purge.stdout


@needs_bash
def test_uninstall_refuses_dangerous_paths():
    assert _run(UNINSTALL, "--data-dir", "/", "--purge-data", "--dry-run").returncode != 0
    assert _run(UNINSTALL, "--prefix", "/usr", "--dry-run").returncode != 0
