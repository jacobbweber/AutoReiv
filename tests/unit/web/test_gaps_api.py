"""
Unit tests for Capability Gaps API router [REQ-FACT-027, REQ-FACT-028].
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ChatMessage, CompletionResponse, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

pytestmark = pytest.mark.slow


class _FakeSynthGateway:
    """CARD-672: stands in for the model. The test used to call whatever OLLAMA_HOST/.env pointed at; a host
    that accepts the connection but never answers held it for the 30 min helper timeout."""

    default_model_id = "fake/synth"

    def __init__(self):
        self.requests = []

    async def complete(self, request, *args, **kwargs):
        self.requests.append(request)
        body = {
            "identified_capability": "Hyper-V Virtual Machine Creation",
            "suggested_tool_name": "create_hyperv_vm",
            "objectives": ["Create a VM with New-VM", "Set startup memory"],
        }
        return CompletionResponse(model="fake/synth", message=ChatMessage(role=Role.ASSISTANT, content=json.dumps(body)))


@pytest.mark.asyncio
async def test_capability_gaps_api_lifecycle(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    fake = _FakeSynthGateway()
    app.state.gateway = fake  # CARD-672: never a real model call from a unit test
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

        # 3. The Factory train route is gone [CARD-497]; the gap stays pending
        train_resp = await ac.post(f"/api/agents/hyperv/gaps/{gap_id}/train")
        assert train_resp.status_code in (404, 405)
        dismiss_first = await ac.delete(f"/api/agents/hyperv/gaps/{gap_id}")
        assert dismiss_first.status_code == 200

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

        # 5. Post a gap with only user prompt and assistant response (synthesizes meaningful capability)
        synth_resp = await ac.post(
            "/api/agents/hyperv/gaps",
            json={
                "user_prompt": "can you try again",
                "assistant_response": "I do not have tools to create VMs. Run New-VM -Name 'test-vm' -MemoryStartupBytes 4GB",
                "session_id": "sess_synth",
            },
        )
        assert synth_resp.status_code == 200
        synth_data = synth_resp.json()
        assert synth_data["success"] is True
        assert "Virtual Machine" in synth_data["gap"]["identified_capability"] or "New-VM" in synth_data["gap"]["identified_capability"]
        assert synth_data["gap"]["suggested_tool_name"] is not None
        # The synthesis went to the fake model once, as a background helper call
        assert len(fake.requests) == 1
        assert fake.requests[0].background is True
        assert synth_data["gap"]["suggested_tool_name"] == "create_hyperv_vm"


@pytest.mark.asyncio
async def test_capability_gap_synthesis_falls_back_without_a_model(tmp_path, monkeypatch):
    """CARD-672: with no gateway the keyword fallback names the capability; no network involved."""
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    app = create_app(state_store=SQLiteStateStore(db_path=str(db_path)))
    app.state.gateway = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/agents/hyperv/gaps",
            json={
                "user_prompt": "can you try again",
                "assistant_response": "I do not have tools to create VMs. Run New-VM -Name 'test-vm' -MemoryStartupBytes 4GB",
            },
        )
    assert resp.status_code == 200
    gap = resp.json()["gap"]
    assert gap["identified_capability"]
    assert gap["suggested_tool_name"] is not None
