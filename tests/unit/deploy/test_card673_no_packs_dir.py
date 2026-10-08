"""CARD-673: packs were removed, so no installer creates an empty packs/ folder in the data dir.

Script-level checks only. Existing packs/ folders on installed systems are left alone (no deletion logic).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALL = ROOT / "deploy" / "systemd" / "install_systemd.sh"
DOCKERFILE = ROOT / "Dockerfile"
README = ROOT / "deploy" / "README.md"
WINDOWS = sorted((ROOT / "deploy" / "windows").glob("*.ps1"))


def _mkdir_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if re.search(r"\bmkdir\b|New-Item", ln)]


def test_systemd_installer_does_not_create_packs():
    lines = _mkdir_lines(INSTALL.read_text(encoding="utf-8"))
    assert lines, "installer still creates the data layout"
    assert not [ln for ln in lines if "packs" in ln], lines


def test_dockerfile_does_not_create_packs():
    lines = _mkdir_lines(DOCKERFILE.read_text(encoding="utf-8"))
    assert any("/data/" in ln for ln in lines), "image still creates /data mount points"
    assert not [ln for ln in lines if "packs" in ln], lines


def test_windows_scripts_do_not_create_packs():
    for script in WINDOWS:
        assert not [ln for ln in _mkdir_lines(script.read_text(encoding="utf-8")) if "packs" in ln], script.name


def test_readme_data_layout_has_no_packs_folder():
    text = README.read_text(encoding="utf-8")
    assert "packs/" not in text.replace("platform-packs/", "")
    assert "/data/packs" not in text
