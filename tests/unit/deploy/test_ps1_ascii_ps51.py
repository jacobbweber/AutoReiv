"""Every deploy PowerShell script must be pure ASCII and parse under Windows PowerShell 5.1.

PowerShell 5.1 reads BOM-less UTF-8 as the ANSI code page, so emoji bytes become smart
quotes and break string literals ("The string is missing the terminator").
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PS1_FILES = sorted([*(ROOT / "deploy").rglob("*.ps1"), *(ROOT / "scripts").rglob("*.ps1")])


def test_ps1_files_found():
    assert any(p.name == "install_windows_service.ps1" for p in PS1_FILES)


@pytest.mark.parametrize("path", PS1_FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_ps1_is_pure_ascii(path: Path):
    data = path.read_bytes()
    bad = [
        (lineno, line.decode("utf-8", "replace").strip()[:60])
        for lineno, line in enumerate(data.splitlines(), 1)
        if any(b > 0x7F for b in line)
    ]
    assert not bad, f"non-ASCII bytes (breaks Windows PowerShell 5.1): {bad}"


POWERSHELL_51 = shutil.which("powershell.exe") or shutil.which("powershell")


@pytest.mark.skipif(POWERSHELL_51 is None, reason="Windows PowerShell 5.1 not available")
@pytest.mark.parametrize("path", PS1_FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_ps1_parses_in_windows_powershell_51(path: Path):
    script = (
        "$e=$null; [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{path}', [ref]$null, [ref]$e) | Out-Null; "
        "$e | ForEach-Object { $_.Extent.StartLineNumber.ToString() + ': ' + $_.Message }; "
        "exit $e.Count"
    )
    res = subprocess.run(
        [POWERSHELL_51, "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert res.returncode == 0, f"parse errors in {path.name}: {res.stdout.strip()} {res.stderr.strip()}"
