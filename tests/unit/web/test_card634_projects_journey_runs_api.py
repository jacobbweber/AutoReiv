"""CARD-634: Projects Studio API lists journey runs from the CARD-532 report root."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import projects as projects_router


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "autoreiv-qa"
    card = root / "card-demo"
    card.mkdir(parents=True)
    report = {
        "title": "AutoReiv live QA",
        "startedAt": "Mon Oct 05 2026 12:00:00",
        "base": "http://127.0.0.1:8770",
        "runs": [
            {
                "journey": "card-demo",
                "viewport": "phone",
                "outcome": "fail",
                "steps": [
                    {"step": "Open app", "status": "pass", "reason": "", "screenshot": "", "ms": 1},
                    {
                        "step": "Click Save",
                        "status": "fail",
                        "reason": "dead",
                        "screenshot": str(card / "fail.png"),
                        "ms": 2,
                    },
                ],
                "notes": [],
                "consoleErrors": [],
                "failedRequests": [],
            }
        ],
    }
    (card / "report.json").write_text(json.dumps(report), encoding="utf-8")
    (card / "summary.md").write_text("# fail\n", encoding="utf-8")
    (card / "fail.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setenv("AUTOREIV_QA_REPORT_DIR", str(root))

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    app = FastAPI()
    app.include_router(projects_router.router)
    app.state.store = store
    return TestClient(app)


def test_list_and_detail_journey_runs(client):
    listed = client.get("/api/projects/journey-runs")
    assert listed.status_code == 200
    body = listed.json()
    assert body["success"] is True
    assert any(r["card"] == "card-demo" and r["overall"] == "fail" for r in body["runs"])
    demo = next(r for r in body["runs"] if r["card"] == "card-demo")
    assert demo["failing_step"] == "Click Save"

    detail = client.get("/api/projects/journey-runs/card-demo")
    assert detail.status_code == 200
    d = detail.json()
    assert d["success"] is True
    assert "Click Save" in d["summary"]
    assert any(s["name"] == "fail.png" for s in d["screenshots"])


def test_missing_run_404(client):
    res = client.get("/api/projects/journey-runs/card-missing")
    assert res.status_code == 404
