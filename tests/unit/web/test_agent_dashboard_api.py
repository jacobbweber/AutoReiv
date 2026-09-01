import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app():
    store = SQLiteStateStore(db_path=":memory:")
    return create_app(state_store=store)


@pytest.mark.asyncio
async def test_dashboard_api_crud_and_discovery(app):
    # 1. Initially no dashboards
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_resp = await ac.get("/api/agent-packs/dashboards")
        assert list_resp.status_code == 200
        assert isinstance(list_resp.json(), list)

        # 2. Save a dashboard for "gardening"
        payload = {
            "tab_title": "Garden Studio",
            "icon": "sprout",
            "description": "Gardening dashboard",
            "cards": [
                {
                    "id": "sensors",
                    "type": "stat_group",
                    "title": "Sensors",
                    "stats": [
                        {"id": "moisture", "label": "Moisture", "value": "70%"}
                    ],
                }
            ],
        }
        post_resp = await ac.post("/api/agent-packs/gardening/dashboard", json=payload)
        assert post_resp.status_code == 200
        saved = post_resp.json()
        assert saved["pack_id"] == "gardening"
        assert saved["tab_title"] == "Garden Studio"

        # 3. Read it back
        get_resp = await ac.get("/api/agent-packs/gardening/dashboard")
        assert get_resp.status_code == 200
        assert get_resp.json()["tab_title"] == "Garden Studio"

        # 4. Appears in discovery list
        list_again = await ac.get("/api/agent-packs/dashboards")
        assert list_again.status_code == 200
        dash_ids = [d["pack_id"] for d in list_again.json()]
        assert "gardening" in dash_ids


@pytest.mark.asyncio
async def test_dashboard_action_execution(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        action_resp = await ac.post(
            "/api/agent-packs/assistant/action",
            json={
                "tool": "get_weekly_summary",
                "args": {},
            },
        )
        assert action_resp.status_code == 200
        result = action_resp.json()
        assert "success" in result
        assert result["tool_name"] == "get_weekly_summary"

