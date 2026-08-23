"""
Integration tests for MCP Server Configuration REST API [REQ-MCP-006].
"""

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
    with TestClient(app) as tc:
        yield tc


def test_mcp_servers_rest_api(client):
    # 1. Initially empty
    res = client.get("/api/mcp/servers")
    assert res.status_code == 200
    assert res.json() == []

    # 2. Add an MCP server
    server_payload = {
        "name": "sqlite-mcp",
        "command": ["npx", "-y", "@modelcontextprotocol/server-sqlite", "data/test.db"],
        "env": {"DEBUG": "true"},
        "enabled": True,
    }
    res = client.post("/api/mcp/servers", json=server_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "saved"
    assert data["name"] == "sqlite-mcp"

    # 3. List contains newly added server
    res = client.get("/api/mcp/servers")
    assert res.status_code == 200
    servers = res.json()
    assert len(servers) == 1
    assert servers[0]["name"] == "sqlite-mcp"
    assert servers[0]["command"] == ["npx", "-y", "@modelcontextprotocol/server-sqlite", "data/test.db"]
