"""
CARD-717: MCP Vault Credential Authentication (Bearer, Basic, Header, Env) and startup/mount resolution.
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.gateway.models import ToolDefinition
from src.domain.security.vault import Credential
from src.domain.settings.models import MCPServerConfig
from src.web.mcp_mount_reconcile import reconcile_saved_mcp_server, resolve_mcp_server_auth


def _make_store(credentials: dict[str, Credential]):
    store = MagicMock()
    store.get_credential.side_effect = lambda cid: credentials.get(cid)
    return store


def test_resolve_mcp_server_auth_bearer_token():
    """Bearer auth injects Authorization: Bearer <secret> from the Vault without mutating stored config."""
    store = _make_store(
        {
            "my-bearer-cred": Credential(
                id="my-bearer-cred",
                name="My HTTP MCP Token",
                type="token",
                secret="secret-bearer-xyz",
            )
        }
    )
    cfg = MCPServerConfig(
        name="http-mcp",
        transport="sse",
        url="http://127.0.0.1:8090/sse",
        credential_id="my-bearer-cred",
        auth_type="bearer",
        enabled=True,
    )
    resolved = resolve_mcp_server_auth(cfg, store)
    assert resolved["headers"] == {"Authorization": "Bearer secret-bearer-xyz"}
    assert cfg.headers is None


def test_resolve_mcp_server_auth_basic_encodes_user_pass():
    """Basic auth base64-encodes user:pass secrets into Authorization: Basic <b64>."""
    store = _make_store(
        {
            "basic-cred": Credential(
                id="basic-cred",
                name="Basic Cred",
                type="basic_auth",
                secret="alice:wonderland123",
            )
        }
    )
    cfg = MCPServerConfig(
        name="basic-mcp",
        transport="sse",
        url="http://127.0.0.1:8090/sse",
        credential_id="basic-cred",
        auth_type="basic",
        enabled=True,
    )
    resolved = resolve_mcp_server_auth(cfg, store)
    expected_b64 = base64.b64encode(b"alice:wonderland123").decode("ascii")
    assert resolved["headers"] == {"Authorization": f"Basic {expected_b64}"}


def test_resolve_mcp_server_auth_custom_header_and_env():
    """Custom header and stdio env auth types inject into headers or env respectively."""
    store = _make_store(
        {
            "api-key-cred": Credential(
                id="api-key-cred",
                name="API Key",
                type="api_key",
                secret="key-999",
            )
        }
    )
    header_cfg = MCPServerConfig(
        name="header-mcp",
        transport="sse",
        url="http://127.0.0.1:8090/sse",
        credential_id="api-key-cred",
        auth_type="header",
        auth_header="X-Custom-Token",
    )
    res_header = resolve_mcp_server_auth(header_cfg, store)
    assert res_header["headers"] == {"X-Custom-Token": "key-999"}

    env_cfg = MCPServerConfig(
        name="stdio-mcp",
        transport="stdio",
        command=["uvx", "mcp-github"],
        credential_id="api-key-cred",
        auth_type="env",
        auth_header="GITHUB_PERSONAL_ACCESS_TOKEN",
    )
    res_env = resolve_mcp_server_auth(env_cfg, store)
    assert res_env["env"] == {"GITHUB_PERSONAL_ACCESS_TOKEN": "key-999"}


@pytest.mark.asyncio
async def test_reconcile_saved_mcp_server_injects_vault_credential():
    """reconcile_saved_mcp_server resolves credential_id via store before mounting."""
    store = _make_store(
        {
            "mcp-token": Credential(
                id="mcp-token",
                name="MCP Bearer",
                type="token",
                secret="tok_live_abc123",
            )
        }
    )
    mcp_manager = MagicMock()
    mcp_manager.mount_server = AsyncMock(
        return_value=[
            ToolDefinition(
                name="mcp_remote_ping",
                description="Ping remote",
                parameters={"type": "object", "properties": {}},
            )
        ]
    )

    cfg = MCPServerConfig(
        name="remote",
        transport="sse",
        url="https://mcp.example.com/sse",
        credential_id="mcp-token",
        auth_type="bearer",
        enabled=True,
    )
    outcome = await reconcile_saved_mcp_server(mcp_manager, cfg, store=store)
    assert outcome["mounted"] is True
    assert outcome["tool_names"] == ["mcp_remote_ping"]
    mcp_manager.mount_server.assert_awaited_once_with(
        name="remote",
        command=None,
        env=None,
        transport="sse",
        url="https://mcp.example.com/sse",
        headers={"Authorization": "Bearer tok_live_abc123"},
    )


@pytest.mark.asyncio
async def test_settings_save_and_list_mcp_with_vault_credential():
    """Saving an MCP server in settings persists credential_id (not plaintext secret) and mounts with Bearer header."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.web.routers.settings import router as settings_router

    app = FastAPI()
    app.include_router(settings_router)

    stored_settings: dict = {}
    cred = Credential(
        id="vault-bearer-1",
        name="Production MCP Bearer",
        type="token",
        secret="super-secret-jwt-token",
    )
    store = MagicMock()
    store.get_setting.side_effect = lambda k, default=None: stored_settings.get(k, default)
    store.set_setting.side_effect = lambda k, v: stored_settings.__setitem__(k, v)
    store.get_credential.side_effect = lambda cid: cred if cid == "vault-bearer-1" else None

    mcp_manager = MagicMock()
    mcp_manager.get_mounted_servers.return_value = {
        "prod-http": {"tool_count": 1, "tools": ["mcp_prod_http_status"]}
    }
    mcp_manager.get_mount_errors.return_value = {}
    mcp_manager.mount_server = AsyncMock(
        return_value=[
            ToolDefinition(
                name="mcp_prod_http_status",
                description="Status",
                parameters={"type": "object", "properties": {}},
            )
        ]
    )

    app.state.store = store
    app.state.mcp_manager = mcp_manager

    client = TestClient(app)
    resp = client.post(
        "/api/settings/mcp",
        json={
            "name": "prod-http",
            "transport": "sse",
            "url": "http://127.0.0.1:9100/sse",
            "credential_id": "vault-bearer-1",
            "auth_type": "bearer",
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["mounted"] is True

    # Verify stored setting never contains the raw secret
    saved_list = stored_settings["mcp_servers"]
    assert len(saved_list) == 1
    assert saved_list[0]["credential_id"] == "vault-bearer-1"
    assert saved_list[0]["auth_type"] == "bearer"
    assert "super-secret-jwt-token" not in str(saved_list)

    # Verify mount_server received the decrypted Authorization header
    mcp_manager.mount_server.assert_awaited_once_with(
        name="prod-http",
        command=None,
        env=None,
        transport="sse",
        url="http://127.0.0.1:9100/sse",
        headers={"Authorization": "Bearer super-secret-jwt-token"},
    )

    # Verify GET /api/settings/mcp includes credential_id and credential_name, never secret
    list_resp = client.get("/api/settings/mcp")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert rows[0]["credential_id"] == "vault-bearer-1"
    assert rows[0]["credential_name"] == "Production MCP Bearer"
    assert "super-secret-jwt-token" not in list_resp.text

    # Verify POST /api/settings/mcp/test also resolves the Vault credential
    with patch("src.web.routers.settings.MCPClientAdapter") as mock_adapter_cls:
        mock_instance = MagicMock()
        mock_instance.list_tools = AsyncMock(return_value=[])
        mock_instance.close = AsyncMock()
        mock_instance.last_error = None
        mock_adapter_cls.return_value = mock_instance

        test_resp = client.post(
            "/api/settings/mcp/test",
            json={
                "name": "prod-http",
                "transport": "sse",
                "url": "http://127.0.0.1:9100/sse",
                "credential_id": "vault-bearer-1",
                "auth_type": "bearer",
                "enabled": True,
            },
        )
        assert test_resp.status_code == 200
        _, kwargs = mock_adapter_cls.call_args
        assert kwargs["headers"] == {"Authorization": "Bearer super-secret-jwt-token"}
