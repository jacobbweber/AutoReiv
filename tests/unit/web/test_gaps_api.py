"""
Unit tests for Capability Gaps API router [REQ-FACT-027, REQ-FACT-028].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_capability_gaps_api_lifecycle(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Post a new capability gap
        create_resp = await ac.post(
            "/api/agents/hyperv/gaps",
            json={
                "turn_text": "can you create me a vm named 'billy'",
                "identified_capability": "Create Hyper-V VM",
                "suggested_tool_name": "manage_hyperv",
                "session_id": "sess_123",
            },
        )
        assert create_resp.status_code == 200
        gap_data = create_resp.json()
        assert gap_data["success"] is True
        gap_id = gap_data["gap"]["id"]
        assert gap_id.startswith("gap_")
        assert gap_data["gap"]["status"] == "pending"

        # 2. List gaps for agent
        list_resp = await ac.get("/api/agents/hyperv/gaps")
        assert list_resp.status_code == 200
        gaps = list_resp.json()["gaps"]
        assert len(gaps) == 1
        assert gaps[0]["id"] == gap_id

        # Other agent has no gaps
        other_resp = await ac.get("/api/agents/coding/gaps")
        assert other_resp.status_code == 200
        assert len(other_resp.json()["gaps"]) == 0

        # 3. Trigger train on the gap
        train_resp = await ac.post(f"/api/agents/hyperv/gaps/{gap_id}/train")
        assert train_resp.status_code == 200
        train_data = train_resp.json()
        assert train_data["success"] is True
        assert "job_id" in train_data
        assert train_data["job_id"].startswith("fjob_")

        # Now pending list should be empty
        list_resp2 = await ac.get("/api/agents/hyperv/gaps")
        assert list_resp2.status_code == 200
        assert len(list_resp2.json()["gaps"]) == 0

        # 4. Create another gap and dismiss it
        create_resp2 = await ac.post(
            "/api/agents/hyperv/gaps",
            json={
                "turn_text": "delete all snapshots",
                "identified_capability": "Snapshot purge",
            },
        )
        gap2_id = create_resp2.json()["gap"]["id"]

        del_resp = await ac.delete(f"/api/agents/hyperv/gaps/{gap2_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

        # Pending list is again empty
        list_resp3 = await ac.get("/api/agents/hyperv/gaps")
        assert len(list_resp3.json()["gaps"]) == 0
