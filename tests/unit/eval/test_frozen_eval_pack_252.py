"""CARD-252: frozen operator eval pack is CI-scriptable (structure + smoke artifacts)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "notes" / "frozen-eval-pack-252.json"
RUNNER = ROOT / "notes" / "scripts" / "frozen_eval_pack_252.py"


@pytest.fixture(scope="module")
def pack() -> dict:
    assert PACK.is_file(), f"missing pack {PACK}"
    return json.loads(PACK.read_text(encoding="utf-8"))


def test_pack_file_and_runner_exist():
    assert PACK.is_file()
    assert RUNNER.is_file()
    assert (ROOT / "notes" / "frozen-eval-pack-252.md").is_file()


def test_pack_has_3_to_5_asks_covering_required_studios(pack: dict):
    asks = pack["asks"]
    assert 3 <= len(asks) <= 5
    studios = {a["studio"] for a in asks}
    assert {"Chat", "Education", "Wiki", "Forge"} <= studios


def test_each_ask_has_observe_checklist_and_prompt(pack: dict):
    for ask in pack["asks"]:
        assert ask["id"]
        assert isinstance(ask["prompt"], str) and len(ask["prompt"]) >= 20
        assert ask["observe_checklist"]
        assert ask["expect"]
        assert ask["evidence_smoke"].startswith("notes/marathon-card")


def test_forge_resume_ask_present(pack: dict):
    forge = [a for a in pack["asks"] if a.get("requires_same_job_resume")]
    assert len(forge) == 1
    assert forge[0]["studio"] == "Forge"
    assert "same" in forge[0]["prompt"].lower() or "SAME" in forge[0]["prompt"]


def test_validate_runner_green_on_prior_smokes():
    # Import from notes/scripts without installing
    import importlib.util

    spec = importlib.util.spec_from_file_location("frozen_eval_pack_252", RUNNER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pack = mod.load_pack()
    result = mod.run_validate(pack)
    assert result["struct_errors"] == []
    assert result["ok"] is True, result
    assert all(a["ok"] for a in result["asks"])
    # every ask must have recorded job_id
    for a in result["asks"]:
        assert str(a["job_id"]).startswith("job_")


def test_cli_validate_exit_zero():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--validate"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
