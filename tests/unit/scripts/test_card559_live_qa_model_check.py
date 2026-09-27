"""CARD-559: live QA checks the model first; a dead endpoint exits 4 ("model endpoint down"), not a product failure."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import live_qa  # noqa: E402


def test_check_model_is_false_when_the_endpoint_is_unreachable():
    assert live_qa.check_model("http://127.0.0.1:9/v1", "m", timeout=1) is False


def test_check_model_subcommand_exits_4_and_names_the_cause(monkeypatch, capsys):
    monkeypatch.setattr(live_qa, "check_model", lambda *a, **k: False)
    assert live_qa.main(["check-model"]) == live_qa.EXIT_MODEL_DOWN == 4
    assert "model endpoint down" in capsys.readouterr().out
    monkeypatch.setattr(live_qa, "check_model", lambda *a, **k: True)
    assert live_qa.main(["check-model"]) == 0


def test_run_stops_before_any_journey_when_the_model_is_down(monkeypatch):
    calls = []
    monkeypatch.setattr(live_qa, "check_model", lambda *a, **k: False)
    monkeypatch.setattr(live_qa, "start", lambda *a, **k: calls.append("start") or 0)
    monkeypatch.setattr(live_qa.subprocess, "call", lambda *a, **k: calls.append("run") or 0)
    assert live_qa.main(["run", "--journeys", "card-520"]) == 4
    assert calls == []


def test_a_product_failure_is_not_retried_while_the_model_is_up(monkeypatch, tmp_path):
    runs = []
    monkeypatch.setenv("AUTOREIV_QA_REPORT_ROOT", str(tmp_path))
    monkeypatch.setattr(live_qa, "check_model", lambda *a, **k: True)
    monkeypatch.setattr(live_qa, "list_journeys", lambda *a, **k: ["card-520-teach-needs-tool"])
    monkeypatch.setattr(live_qa, "start", lambda *a, **k: 0)
    monkeypatch.setattr(live_qa, "stop", lambda *a, **k: True)
    monkeypatch.setattr(live_qa, "git_status", lambda *a, **k: "")
    monkeypatch.setattr(live_qa, "append_checkout_guard", lambda *a, **k: None)
    monkeypatch.setattr(live_qa.subprocess, "call", lambda cmd, **k: runs.append(cmd) or 1)
    assert live_qa.main(["run", "--journeys", "card-520", "--viewports", "desktop", "--attempts", "3"]) == 1
    assert len(runs) == 1
    assert runs[0][runs[0].index("--attempts") + 1] == "1"
