"""
Tests for Agent Origin API surfacing and deletion constraints [REQ-RECON-005].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app():
    store = SQLiteStateStore(db_path=":memory:")
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_api_agents_surfaces_origin_and_restricts_deletion(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Query agents roster
        resp = await ac.get("/api/agents")
        assert resp.status_code == 200
        agents = resp.json()
        agent_map = {a["id"]: a for a in agents}

        # Verify origin surfaced on packs & system agents
        assert "origin" in agent_map["autoreiv"]
        assert agent_map["autoreiv"]["origin"] == "pack"

        assert "agent-builder" not in agent_map
        dev = agent_map["developer"]
        assert "propose_skill" in (dev.get("allowed_tool_names") or dev.get("allowed_tools") or [])

        # 2. Create agent pack and verify origin is "pack"
        custom_payload = {
            "id": "operator-assistant",
            "name": "Operator Assistant",
            "description": "Custom agent",
            "system_prompt": "You are a custom operator assistant for daily tasks.",
            "allowed_tool_names": [],
        }
        create_resp = await ac.post("/api/agents", json=custom_payload)
        assert create_resp.status_code == 200

        # Query created agent
        get_resp = await ac.get("/api/agents/operator-assistant")
        assert get_resp.status_code == 200
        assert get_resp.json()["origin"] == "pack"

        # 3. Forbid DELETE on autoreiv core agent
        del_platform = await ac.delete("/api/agents/autoreiv")
        assert del_platform.status_code in (400, 403)

        # 4. Retired agent-builder is not a live agent to delete
        del_system = await ac.delete("/api/agents/agent-builder")
        assert del_system.status_code == 404

        # 5. Allow DELETE on agent pack
        del_custom = await ac.delete("/api/agents/operator-assistant")
        assert del_custom.status_code == 200
        assert del_custom.json()["status"] == "deleted"
