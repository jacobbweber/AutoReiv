"""CARD-272: install / Compose / update truth locks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_compose_persists_data_dir():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "AUTOREIV_DATA_DIR=/data" in text
    assert "/data" in text
    assert "autoreiv-data" in text or "volumes:" in text


def test_install_scripts_exist():
    win = ROOT / "deploy" / "windows" / "install_windows_service.ps1"
    linux = ROOT / "deploy" / "systemd" / "install_systemd.sh"
    assert win.is_file() and win.stat().st_size > 100
    assert linux.is_file() and linux.stat().st_size > 100
    assert "service" in win.read_text(encoding="utf-8", errors="ignore").lower()
    assert "systemd" in linux.read_text(encoding="utf-8", errors="ignore").lower() or "systemctl" in linux.read_text(
        encoding="utf-8", errors="ignore"
    ).lower()


def test_settings_wires_version_and_check():
    js = (ROOT / "src" / "web" / "static" / "modules" / "studios" / "settings.js").read_text(
        encoding="utf-8"
    )
    assert "/api/system/version" in js
    assert "/api/system/updates/check" in js
    assert "/api/system/updates/apply" in js
