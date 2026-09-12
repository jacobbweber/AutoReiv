"""CARD-266: Observe receipt — existing job_id opens; unknown is real 404."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def _app_with_job(tmp_path: Path):
    store = SQLiteStateStore(db_path=str(tmp_path / "ctrl266.db"))
    store.initialize_db()
    orch = JobPhaseOrchestrator(store, data_dir=tmp_path)
    job = orch.create_job_with_phases(
        goal="CARD-266 receipt proof",
        session_id="sess_obs266",
        agent_id="assistant",
        phase_specs=[{"name": "Execute", "success_rule": "done"}],
    )
    app = create_app(state_store=store)
    return app, job.id


def test_req_obsrec_001_canonical_get_opens_existing_job(tmp_path):
    app, jid = _app_with_job(tmp_path)
    client = TestClient(app)
    res = client.get(f"/api/observe/jobs/{jid}")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ok"] is True
    assert data["job_id"] == jid
    assert data["job"]["id"] == jid
    assert data["job"]["goal"]


def test_req_obsrec_001_jobs_alias_opens_existing_job(tmp_path):
    app, jid = _app_with_job(tmp_path)
    client = TestClient(app)
    res = client.get(f"/api/jobs/{jid}")
    assert res.status_code == 200, res.text
    assert res.json()["job_id"] == jid


def test_req_obsrec_002_unknown_job_is_real_404(tmp_path):
    app, _ = _app_with_job(tmp_path)
    client = TestClient(app)
    missing = "job_doesnotexist999"
    for url in (
        f"/api/observe/jobs/{missing}",
        f"/api/jobs/{missing}",
        f"/api/observability/standing-journey?job_id={missing}",
    ):
        res = client.get(url)
        assert res.status_code == 404, (url, res.status_code, res.text)
        body = res.json()
        detail = body.get("detail", body)
        if isinstance(detail, dict):
            assert detail.get("ok") is False
            assert missing in str(detail.get("job_id") or detail)
        else:
            assert "not found" in str(detail).lower() or missing in str(detail)


def test_req_obsrec_001_standing_journey_still_opens_existing(tmp_path):
    app, jid = _app_with_job(tmp_path)
    client = TestClient(app)
    res = client.get(f"/api/observability/standing-journey?job_id={jid}")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["job_id"] == jid
