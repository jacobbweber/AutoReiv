"""CARD-668: one short install/uninstall doc that matches the real installers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "install-and-uninstall.md"


def _doc() -> str:
    assert DOC.is_file(), "docs/install-and-uninstall.md is missing"
    return DOC.read_text(encoding="utf-8")


def test_doc_has_three_sections():
    text = _doc()
    for heading in ("## Windows service", "## Linux systemd", "## Docker"):
        assert heading in text, heading


def test_doc_names_data_paths_and_overrides():
    text = _doc()
    for needle in (
        r"%LOCALAPPDATA%\AutoReiv",
        "-DataDir",
        "/opt/autoreiv",
        "/var/lib/autoreiv",
        "--prefix",
        "--data-dir",
        "/data",
        "AUTOREIV_WIKI_HOST_PATH",
    ):
        assert needle in text, needle


def test_doc_says_uninstall_keeps_data_and_names_wipe_steps():
    text = _doc().lower()
    assert "uninstall never deletes" in text
    assert "--purge-data" in text
    assert "docker compose down -v" in text


def test_doc_flags_match_installers():
    win_install = (ROOT / "deploy/windows/install_windows_service.ps1").read_text(encoding="utf-8")
    sd_install = (ROOT / "deploy/systemd/install_systemd.sh").read_text(encoding="utf-8")
    sd_uninstall = (ROOT / "deploy/systemd/uninstall_systemd.sh").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "DataDir" in win_install
    assert "--prefix" in sd_install and "--data-dir" in sd_install
    assert "/var/lib/autoreiv" in sd_install and "/opt/autoreiv" in sd_install
    assert "--purge-data" in sd_uninstall
    assert "autoreiv-data:/data" in compose


def test_doc_is_linked_from_readme_and_deploy_readme():
    for rel in ("README.md", "deploy/README.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "install-and-uninstall.md" in text, rel
