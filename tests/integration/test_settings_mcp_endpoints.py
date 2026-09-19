"""
Integration tests verifying Settings MCP endpoints support transport (stdio/sse), url, and headers
[REQ-MCP-HANDSHAKE-003].
"""

from unittest.mock import AsyncMock, patch

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
    if hasattr(app.state, "mcp_manager") and app.state.mcp_manager:
        app.state.mcp_manager.mount_server = AsyncMock(return_value=[])
        app.state.mcp_manager.unmount_server = AsyncMock()

    with TestClient(app) as tc:
        yield tc, app


def test_save_mcp_server_remote_sse(client):
    tc, app = client
    payload = {
        "name": "remote-blender",
        "transport": "sse",
        "url": "http://127.0.0.1:9191/sse",
        "headers": {"Authorization": "Bearer token123"},
        "enabled": True,
    }

    res = tc.post("/api/settings/mcp", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "saved"
    assert data["name"] == "remote-blender"

    # Verify mount_server was called with transport="sse", url, headers
    app.state.mcp_manager.mount_server.assert_called_once_with(
        name="remote-blender",
        command=None,
        env=None,
        transport="sse",
        url="http://127.0.0.1:9191/sse",
        headers={"Authorization": "Bearer token123"},
    )


def test_test_mcp_server_remote_sse(client):
    tc, _ = client
    payload = {
        "name": "test-remote",
        "transport": "sse",
        "url": "http://127.0.0.1:9191/sse",
        "headers": {"X-Custom": "header-val"},
    }

    with patch("src.web.routers.settings.MCPClientAdapter") as mock_adapter_cls:
        mock_instance = AsyncMock()
        mock_instance.list_tools = AsyncMock(return_value=[])
        mock_adapter_cls.return_value = mock_instance

        res = tc.post("/api/settings/mcp/test", json=payload)
        assert res.status_code == 200
        mock_adapter_cls.assert_called_once()
        _, kwargs = mock_adapter_cls.call_args
        assert kwargs.get("transport") == "sse"
        assert kwargs.get("url") == "http://127.0.0.1:9191/sse"
        assert kwargs.get("headers") == {"X-Custom": "header-val"}
