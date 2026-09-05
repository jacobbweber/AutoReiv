"""Unit tests for Factory Web API [REQ-FACT-005, REQ-FACT-014]."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_factory_jobs_api_lifecycle(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create a factory training job
        resp = await ac.post(
            "/api/factory/jobs",
            json={
                "target_agent_id": "game-agent",
                "seed_intent": "Manage Palworld game server",
                "target_host": "192.168.1.150",
                "objectives": ["Lifecycle", "Config"],
                "risk_policy": "ask",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["status"] == "queued"
        job_id = data["job_id"]
        assert job_id.startswith("fjob_")

        # Verify session was anchored to an autoreiv platform session [REQ-FACT-018]
        assert "session_id" in data
        sess = store.get_session(data["session_id"])
        assert sess is not None
        assert sess.agent_id == "autoreiv"

        # 2. List factory jobs
        list_resp = await ac.get("/api/factory/jobs")
        assert list_resp.status_code == 200
        jobs = list_resp.json()["jobs"]
        assert any(j["id"] == job_id for j in jobs)
        target_summary = next(j for j in jobs if j["id"] == job_id)
        assert "packets_count" in target_summary

        # 3. Step factory job via API [REQ-FACT-017]
        step_resp = await ac.post(f"/api/factory/jobs/{job_id}/step")
        assert step_resp.status_code == 200
        step_data = step_resp.json()
        assert step_data["success"] is True
        assert step_data["stepped"] is True

        # 4. Get single job with packets
        get_resp = await ac.get(f"/api/factory/jobs/{job_id}")
        assert get_resp.status_code == 200
        job_data = get_resp.json()["job"]
        assert job_data["id"] == job_id
        assert job_data["target_agent_id"] == "game-agent"
        assert len(get_resp.json()["packets"]) >= 2

        # 5. 404 on nonexistent job
        non_existent = await ac.get("/api/factory/jobs/fjob_nonexistent")
        assert non_existent.status_code == 404

        # 6. Promote job to user pack
        promote_resp = await ac.post(f"/api/factory/jobs/{job_id}/promote")
        assert promote_resp.status_code == 200
        promote_data = promote_resp.json()
        assert promote_data["success"] is True
        assert promote_data["agent_id"] == "game-agent"

        # Verify pack on disk
        pack_json = data_dir / "packs" / "game-agent" / "pack.json"
        assert pack_json.exists()

        # 7. Delete factory job
        del_resp = await ac.delete(f"/api/factory/jobs/{job_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True
