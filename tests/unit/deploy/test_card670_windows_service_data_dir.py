"""CARD-670: the Windows service installer takes -DataDir and wires AUTOREIV_DATA_DIR into NSSM.

Script-level checks only (no Administrator, no NSSM needed).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALL = (ROOT / "deploy" / "windows" / "install_windows_service.ps1").read_text(encoding="utf-8")
UNINSTALL = (ROOT / "deploy" / "windows" / "uninstall_windows_service.ps1").read_text(encoding="utf-8")


def _param_block(text: str) -> str:
    m = re.search(r"param\s*\((.*?)\)\s*\n", text, re.S | re.I)
    assert m, "script has a param() block"
    return m.group(1)


def test_installer_has_data_dir_parameter_defaulting_to_localappdata():
    params = _param_block(INSTALL)
    assert re.search(r"\[string\]\$DataDir", params)
    assert "LOCALAPPDATA" in INSTALL and "AutoReiv" in INSTALL
    # the default is resolved in the script, not a hard-coded user path
    assert "C:\\Users" not in INSTALL


def test_installer_sets_autoreiv_data_dir_on_the_service():
    assert "AppEnvironmentExtra" in INSTALL
    assert "AUTOREIV_DATA_DIR=" in INSTALL
    line = next(ln for ln in INSTALL.splitlines() if "AppEnvironmentExtra" in ln)
    assert "$DataDir" in line or "$envExtra" in line or "$ServiceEnv" in line


def test_installer_logs_go_under_the_data_dir_not_the_checkout():
    assert "AppStdout" in INSTALL and "AppStderr" in INSTALL
    assert '"$RootPath\\data\\' not in INSTALL
    stdout = next(ln for ln in INSTALL.splitlines() if "AppStdout" in ln)
    assert "$LogDir" in stdout or "$DataDir" in stdout


def test_uninstaller_takes_data_dir_and_never_deletes_it():
    params = _param_block(UNINSTALL)
    assert re.search(r"\[string\]\$DataDir", params)
    for bad in ("Remove-Item", "rmdir", "rd /s", "del /s"):
        assert bad not in UNINSTALL, f"uninstaller must not delete data ({bad})"
    assert "preserved" in UNINSTALL
    assert "$DataDir" in UNINSTALL.split("preserved")[0][-400:]
