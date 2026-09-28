"""CARD-559: new_card.py renders the bug/feature templates; preflight judges stages without stopping on failure."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NEW_CARD = ROOT / ".agents" / "skills" / "card" / "scripts" / "new_card.py"
PREFLIGHT = ROOT / ".agents" / "skills" / "preflight" / "scripts" / "preflight.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_new_card_renders_the_template_for_its_type(tmp_path):
    for kind, heading in (("bug", "## Cause"), ("feature", "## Change")):
        out = subprocess.run([sys.executable, str(NEW_CARD), f"Demo {kind}", "--type", kind, "--slug", kind, "--cards-dir", str(tmp_path)],
                             capture_output=True, text=True, check=True).stdout
        assert "wait for build" in out
        card = next(tmp_path.glob(f"CARD-*-{kind}.md")).read_text(encoding="utf-8")
        assert f"type: {kind}" in card and "proof:" in card and heading in card and "## What dies" in card
    assert sorted(p.name for p in tmp_path.iterdir()) == ["CARD-1-bug.md", "CARD-2-feature.md"]


def test_preflight_names_known_lint_and_treats_no_tests_as_pass(monkeypatch):
    pf = _load(PREFLIGHT, "preflight_559")
    assert pf.KNOWN_LINT == {}  # CARD-454/456 fixed the baseline: no named lint debt
    monkeypatch.setitem(pf.KNOWN_LINT, "ruff", ("CARD-454", 7))
    assert pf.judge("pytest", 0, "", None)[0] == "PASS"
    assert pf.judge("pytest", 5, "no tests ran in 0.1s", None)[0] == "PASS"
    status, note = pf.judge("ruff", 1, "Found 3 errors.", "ruff")
    assert status == "KNOWN" and "CARD-454" in note
    assert pf.judge("ruff", 1, "Found 99 errors.", "ruff")[0] == "FAIL"
    assert pf.judge("pytest", 1, "1 failed", None)[0] == "FAIL"


def test_preflight_maps_changed_src_modules_to_tests():
    pf = _load(PREFLIGHT, "preflight_559b")
    tests = pf.ROOT / "tests"
    found = pf.mapped_tests(["src/application/orchestration/honesty_smoke_pack.py", "README.md"], tests)
    assert "tests/unit/orchestration/test_card261_honesty_smoke_pack.py" in found
    assert pf.mapped_tests(["docs/x.md"], tests) == []


def test_fast_tier_changed_tests_skip_slow_and_nightly_writes_outside_repo(monkeypatch, tmp_path):
    """CARD-560: slow-marked tests leave the fast tier; nightly summaries go to user data, not the repo."""
    pf = _load(PREFLIGHT, "preflight_560")
    monkeypatch.setattr(pf, "changed_files", lambda base: ["tests/unit/skills/test_card559_card_and_preflight_scripts.py"])
    stages = {name: cmd for name, cmd, _ in pf.fast_stages("qa")}
    cmd = stages["pytest changed tests (not slow)"]
    assert ["-m", "not slow"] == cmd[len(pf.PYTEST):len(pf.PYTEST) + 2]
    assert pf.judge("pytest", 5, "3 deselected in 0.4s", None)[0] == "PASS"
    assert pf.nightly_dir({"LOCALAPPDATA": str(tmp_path)}) == tmp_path / "AutoReiv" / "nightly"
    assert pf.nightly_dir({"AUTOREIV_NIGHTLY_DIR": str(tmp_path / "n")}) == tmp_path / "n"
    assert pf.ROOT not in pf.nightly_dir({"LOCALAPPDATA": str(tmp_path)}).parents
