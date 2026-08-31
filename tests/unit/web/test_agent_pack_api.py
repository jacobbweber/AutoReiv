"""CARD-119: show_in_chat persists on agents API and defaults true."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_agents_api_show_in_chat_default_and_hide(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listed = await ac.get("/api/agents")
        assert listed.status_code == 200
        by_id = {row["id"]: row for row in listed.json()}
        assert by_id["assistant"]["show_in_chat"] is True
        assert by_id["autoreiv"]["show_in_chat"] is True
        assert "pack_tool_names" in by_id["assistant"]

        created = await ac.post(
            "/api/agents",
            json={
                "id": "hidden-bot",
                "name": "Hidden Bot",
                "description": "Behind the scenes",
                "system_prompt": "You are a hidden specialist.",
                "show_in_chat": False,
                "pack_tool_names": ["system_info"],
                "allowed_tool_names": ["system_info"],
            },
        )
        assert created.status_code == 200
        got = await ac.get("/api/agents/hidden-bot")
        assert got.status_code == 200
        body = got.json()
        assert body["show_in_chat"] is False
        assert body["pack_tool_names"] == ["system_info"]

        listed2 = {row["id"]: row for row in (await ac.get("/api/agents")).json()}
        assert listed2["hidden-bot"]["show_in_chat"] is False
        assert listed2["assistant"]["show_in_chat"] is True
