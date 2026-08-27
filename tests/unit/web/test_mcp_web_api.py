"""
Integration tests for MCP Server Configuration REST API [REQ-MCP-005].
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    app = create_app(
        state_store=store,
        wiki_path=str(tmp_path / "wiki"),
    )
    # Mock mcp_manager mount_server
    if hasattr(app.state, "mcp_manager") and app.state.mcp_manager:
        from src.domain.gateway.models import ToolDefinition

        app.state.mcp_manager.mount_server = AsyncMock(
            return_value=[
                ToolDefinition(
                    name="mcp_sqlite-mcp_query",
                    description="Run SQL",
                    parameters={"type": "object", "properties": {}},
                )
            ]
        )
        app.state.mcp_manager.unmount_server = AsyncMock()

    with TestClient(app) as tc:
        yield tc


def test_mcp_servers_rest_api_crud(client):
    # 1. Initially empty
    res = client.get("/api/settings/mcp")
    assert res.status_code == 200
    assert res.json() == []

    # 2. Add an MCP server
    server_payload = {
        "name": "sqlite-mcp",
        "command": ["npx", "-y", "@modelcontextprotocol/server-sqlite", "data/test.db"],
        "env": {"DEBUG": "true"},
        "enabled": True,
    }
    res = client.post("/api/settings/mcp", json=server_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "saved"
    assert data["name"] == "sqlite-mcp"
    assert data["mounted"] is True

    # 3. List contains newly added server with mounted status
    res = client.get("/api/settings/mcp")
    assert res.status_code == 200
    servers = res.json()
    assert len(servers) == 1
    assert servers[0]["name"] == "sqlite-mcp"
    assert servers[0]["command"] == ["npx", "-y", "@modelcontextprotocol/server-sqlite", "data/test.db"]

    # 4. Delete MCP server
    del_res = client.delete("/api/settings/mcp/sqlite-mcp")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 5. List is empty again
    res2 = client.get("/api/settings/mcp")
    assert res2.status_code == 200
    assert res2.json() == []
