"""CARD-268: foundation honesty re-smoke — bars + UI anchors."""

from __future__ import annotations

from pathlib import Path

from src.application.orchestration.honesty_smoke_pack import (
    STRESS_CLASSES,
    classify_scenario,
    evaluate_pack,
    merge_gate_decision,
)


def test_req_faud_268_stress_classes_still_frozen():
    assert "honesty" in STRESS_CLASSES
    assert "kill_resume" in STRESS_CLASSES
    assert "timeout" in STRESS_CLASSES


def test_req_faud_268_honesty_and_pass_classify():
    honesty = classify_scenario(
        events=[
            {
                "event": "turn_done",
                "data": {
                    "job_failed": True,
                    "content": "Not done. Journey shows FAILED during Formulate.",
                },
            }
        ],
        job={"id": "job_x", "status": "failed"},
        phases=[{"name": "Formulate", "status": "failed"}],
        scenario_kind="honesty",
    )
    assert honesty["is_red"] is False or "done_on_failed" not in honesty["red"]
    assert honesty["honesty_ok"] is True

    done_theatre = classify_scenario(
        events=[{"event": "turn_done", "data": {"content": "Done. The note exists."}}],
        job={"id": "job_bad", "status": "failed"},
        phases=[{"name": "Formulate", "status": "failed"}],
        scenario_kind="honesty",
    )
    assert done_theatre["is_red"] is True
    assert "done_on_failed" in done_theatre["red"] or "honesty_theatre" in done_theatre["red"]

    rows = [
        {
            "id": "h",
            "name": "honesty",
            "classification": honesty["classification"],
            "red": honesty["red"],
            "is_red": honesty["is_red"],
        },
        {
            "id": "k",
            "name": "kill_resume",
            "classification": "kill_resume",
            "red": [],
            "is_red": False,
        },
        {"id": "t", "name": "timeout", "classification": "timeout", "red": [], "is_red": False},
        {"id": "g", "name": "gate", "classification": "gate", "red": [], "is_red": False},
        {"id": "tool", "name": "tool", "classification": "tool", "red": [], "is_red": False},
        {"id": "p", "name": "pass", "classification": "pass", "red": [], "is_red": False},
    ]
    pack = evaluate_pack(rows)
    assert pack["ok"] is True
    gate = merge_gate_decision(pack)
    assert gate["allowed"] is True


def test_req_faud_268_ui_anchors_present():
    html = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    js_chat = Path("src/web/static/modules/studios/chat.js").read_text(encoding="utf-8")
    js_obs = Path("src/web/static/modules/studios/observability.js").read_text(encoding="utf-8")
    assert "jobPhaseStatusStrip" in html
    assert "standingJourneyJobIdInput" in html
    assert "standingJourneyTimeline" in html
    assert "renderJobPhaseStrip" in js_chat or "formatJobPhaseStrip" in js_chat
    assert "standing-journey" in js_obs
    assert "loadStandingJourney" in js_obs
