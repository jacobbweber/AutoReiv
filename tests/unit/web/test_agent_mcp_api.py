"""
Unit tests for Per-Agent MCP Management API Endpoints [CARD-183].
[REQ-MCP-AGENT-003]
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.mark.asyncio
async def test_agent_mcp_api_crud_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create a test agent
        created = await ac.post(
            "/api/agents",
            json={
                "id": "hyperv",
                "name": "Hyper-V Specialist",
                "description": "Virtual machine manager",
                "system_prompt": "Manage Hyper-V infrastructure.",
            },
        )
        assert created.status_code == 200

        # 2. GET /api/agents/hyperv/mcp - initially empty
        res = await ac.get("/api/agents/hyperv/mcp")
        assert res.status_code == 200
        assert res.json() == []

        # 3. POST /api/agents/hyperv/mcp - add remote MCP server
        save_res = await ac.post(
            "/api/agents/hyperv/mcp",
            json={
                "name": "hyperv-remote",
                "transport": "sse",
                "url": "http://192.168.1.50:8080/sse",
                "headers": {"Authorization": "Bearer hyperv-token"},
                "enabled": False,  # disabled so it doesn't try to connect immediately in unit test
            },
        )
        assert save_res.status_code == 200
        save_data = save_res.json()
        assert save_data["status"] == "saved"
        assert save_data["name"] == "hyperv-remote"

        # 4. GET /api/agents/hyperv/mcp - now contains hyperv-remote
        get_res = await ac.get("/api/agents/hyperv/mcp")
        assert get_res.status_code == 200
        servers = get_res.json()
        assert len(servers) == 1
        assert servers[0]["name"] == "hyperv-remote"
        assert servers[0]["transport"] == "sse"
        assert servers[0]["url"] == "http://192.168.1.50:8080/sse"

        # 5. DELETE /api/agents/hyperv/mcp/hyperv-remote
        del_res = await ac.delete("/api/agents/hyperv/mcp/hyperv-remote")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 6. Verify empty again
        verify_res = await ac.get("/api/agents/hyperv/mcp")
        assert verify_res.status_code == 200
        assert verify_res.json() == []


@pytest.mark.asyncio
async def test_agent_mcp_builtin_override(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Builtin agent 'autoreiv'
        res = await ac.get("/api/agents/autoreiv/mcp")
        assert res.status_code == 200
        assert res.json() == []

        # Add an MCP server to builtin agent
        save_res = await ac.post(
            "/api/agents/autoreiv/mcp",
            json={
                "name": "docker-host",
                "transport": "sse",
                "url": "http://127.0.0.1:9090/sse",
                "enabled": False,
            },
        )
        assert save_res.status_code == 200

        # Retrieve and verify override persisted
        get_res = await ac.get("/api/agents/autoreiv/mcp")
        assert get_res.status_code == 200
        data = get_res.json()
        assert len(data) == 1
        assert data[0]["name"] == "docker-host"
        assert data[0]["url"] == "http://127.0.0.1:9090/sse"


@pytest.mark.asyncio
async def test_agent_mcp_probe_test_endpoint(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    # Mock the remote transport response for the probe
    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {
                            "name": "vm_create",
                            "description": "Create a Hyper-V VM",
                            "inputSchema": {"type": "object"},
                        }
                    ]
                },
            },
        )

    # Monkeypatch MCPClientAdapter to use mock transport
    from src.infrastructure.mcp.client_adapter import MCPClientAdapter
    orig_init = MCPClientAdapter.__init__

    def mock_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        if self.transport == "sse":
            self._http_transport = httpx.MockTransport(handler)

    monkeypatch.setattr(MCPClientAdapter, "__init__", mock_init)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/agents/autoreiv/mcp/test",
            json={
                "name": "mock-hyperv",
                "transport": "sse",
                "url": "http://192.168.1.100:8000/sse",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["server_name"] == "mock-hyperv"
        assert data["tools_count"] == 1
        assert "mcp_mock-hyperv_vm_create" in data["tools"]


@pytest.mark.asyncio
async def test_agent_mcp_mount_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create an agent
        await ac.post(
            "/api/agents",
            json={
                "id": "hyperv",
                "name": "Hyper-V",
                "description": "Hyper-V",
                "system_prompt": "Manage Hyper-V",
            },
        )

        # Save disabled MCP server
        await ac.post(
            "/api/agents/hyperv/mcp",
            json={
                "name": "test-remote",
                "transport": "sse",
                "url": "http://127.0.0.1:8080/sse",
                "enabled": False,
            },
        )

        # Call mount endpoint (will fail to connect to 8080 without running server, but returns graceful status: error)
        res = await ac.post("/api/agents/hyperv/mcp/test-remote/mount")
        assert res.status_code == 200
        data = res.json()
        assert data["server_name"] == "test-remote"
        assert data["status"] in ("mounted", "error")


