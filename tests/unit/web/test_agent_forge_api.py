"""
Integration tests for Agent Forge REST API [REQ-FORGE-006].
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
async def test_agent_forge_crud_api(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Get Skills Catalog
        cat_resp = await ac.get("/api/skills/catalog")
        assert cat_resp.status_code == 200
        cat = cat_resp.json()
        assert "tools" in cat
        assert "purposes" in cat

        # 2. List Agents
        list_resp = await ac.get("/api/agents")
        assert list_resp.status_code == 200
        agents = list_resp.json()
        assert len(agents) >= 5

        # 3. Create Custom Agent
        new_agent = {
            "id": "security-auditor",
            "name": "Security Auditor",
            "description": "SOC2 compliance & vulnerability scanning",
            "system_prompt": "You audit code and infrastructure for CVEs.",
            "purpose": "reasoning",
            "tone": "technical",
            "avatar_icon": "shield-alert",
            "model": "default",
            "allowed_tool_names": ["system_info", "verify_telemetry_consistency"],
            "max_turns": 10,
        }
        create_resp = await ac.post("/api/agents", json=new_agent)
        assert create_resp.status_code == 200
        assert create_resp.json()["status"] == "created"

        # 4. Get Agent by ID
        get_resp = await ac.get("/api/agents/security-auditor")
        assert get_resp.status_code == 200
        agent_data = get_resp.json()
        assert agent_data["name"] == "Security Auditor"
        assert agent_data["purpose"] == "reasoning"
        assert agent_data["avatar_icon"] == "shield-alert"

        # 5. Update Agent
        update_payload = {
            "name": "Lead Security Auditor",
            "description": "SOC2 compliance lead",
            "system_prompt": "You lead security audits.",
            "purpose": "reasoning",
            "tone": "technical",
            "avatar_icon": "shield",
            "model": "default",
            "allowed_tool_names": ["system_info"],
            "max_turns": 15,
        }
        put_resp = await ac.put("/api/agents/security-auditor", json=update_payload)
        assert put_resp.status_code == 200
        assert put_resp.json()["status"] == "updated"

        # 6. Delete Custom Agent
        del_resp = await ac.delete("/api/agents/security-auditor")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        # 7. Cannot delete built-in agent
        bad_del = await ac.delete("/api/agents/linux-sysadmin")
        assert bad_del.status_code == 400
