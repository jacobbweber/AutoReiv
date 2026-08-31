"""Windows launcher must not override CARD-102 data dir with checkout ./data [REQ-DATA-001]."""

from pathlib import Path


def test_windows_launcher_does_not_force_checkout_data_paths():
    text = Path("deploy/windows/run_autoreiv.ps1").read_text(encoding="utf-8")
    assert '$DbPath = Join-Path $RootPath "data\\autoreiv.db"' not in text
    assert '$WikiPath = Join-Path $RootPath "data\\wiki"' not in text
    assert '"--db-path", $DbPath, "--wiki-path", $WikiPath' not in text
    assert "AUTOREIV_DATA_DIR" in text
    assert "LOCALAPPDATA" in text
