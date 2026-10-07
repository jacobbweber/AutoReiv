"""CARD-657: pytest exit code 5 (no tests collected) is PASS, even when xdist omits 'deselected'."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = ROOT / ".agents" / "skills" / "preflight" / "scripts" / "preflight.py"


def _load():
    spec = importlib.util.spec_from_file_location("preflight_657", PREFLIGHT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_exit_5_without_deselected_text_is_pass():
    """The CARD-656 false fail: xdist left only a warnings line, no 'deselected' / 'no tests ran'."""
    pf = _load()
    status, note = pf.judge("pytest changed tests (not slow)", 5, "32 warnings in 6.11s", None)
    assert status == "PASS", f"expected PASS, got {status!r} with note {note!r}"
    assert "no tests selected" in note
    assert pf.judge("pytest", 5, "", None) == ("PASS", "no tests selected")
    # Real failures still fail; lint exit codes are not this path.
    assert pf.judge("pytest", 1, "1 failed", None)[0] == "FAIL"
    assert pf.judge("ruff", 5, "something", "ruff")[0] == "FAIL"


def test_exit_5_with_classic_text_still_passes():
    pf = _load()
    assert pf.judge("pytest", 5, "no tests ran in 0.1s", None)[0] == "PASS"
    assert pf.judge("pytest", 5, "3 deselected in 0.4s", None)[0] == "PASS"
