"""
Operator contract: MCP disable unmounts and enable remounts [CARD-424].

REQ-424-001 platform disable persists enabled false and unmounts.
REQ-424-002 enable persists enabled true and mounts, or reports mount failure.
REQ-424-003 agent disable unmounts that server only.
REQ-424-004 list is_mounted and tools match post-disable reality.
REQ-424-005 delete is not the only path that unmounts.
"""

import pytest
from fastapi.testclient import TestClient

from src.domain.gateway.models import ToolDefinition
from src.infrastructure.mcp.client_adapter import MCPClientAdapter
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    async def fake_list_tools(self):
        return [
            ToolDefinition(
                name=f"mcp_{self.server_name}_ping",
                description="ping",
                parameters={"type": "object"},
            )
        ]

    async def fake_close(self):
        return None

    monkeypatch.setattr(MCPClientAdapter, "list_tools", fake_list_tools)
    monkeypatch.setattr(MCPClientAdapter, "close", fake_close)

    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    store.initialize_db()
    app = create_app(state_store=store, wiki_path=str(tmp_path / "wiki"))
    with TestClient(app) as tc:
        yield tc, app


def _sse(name: str, enabled: bool) -> dict:
    return {
        "name": name,
        "transport": "sse",
        "url": "http://127.0.0.1:9/sse",
        "headers": {"Authorization": "Bearer card-424"},
        "enabled": enabled,
    }


def _row(servers, name: str) -> dict:
    match = next((server for server in servers if server.get("name") == name), None)
    assert match is not None, name
    return match


def _catalog_names(tc: TestClient) -> set[str]:
    res = tc.get("/api/agent_training_factory/capabilities")
    assert res.status_code == 200
    names = set()
    for ns in res.json().get("namespaces") or []:
        for tool in ns.get("tools") or []:
            if tool.get("name"):
                names.add(tool["name"])
    return names


def test_platform_disable_unmounts_and_enable_remounts(client):
    """REQ-424-001, REQ-424-002, REQ-424-004, REQ-424-005."""
    tc, app = client
    enabled = tc.post("/api/settings/mcp", json=_sse("hyperv", True))
    assert enabled.status_code == 200
    enabled_body = enabled.json()
    assert enabled_body["status"] == "saved"
    assert enabled_body["mounted"] is True
    assert "mcp_hyperv_ping" in enabled_body["tools"]

    mounted = _row(tc.get("/api/settings/mcp").json(), "hyperv")
    assert mounted["enabled"] is True
    assert mounted["is_mounted"] is True
    assert mounted["tool_count"] == 1
    assert mounted["tools"] == ["mcp_hyperv_ping"]
    assert "mcp_hyperv_ping" in _catalog_names(tc)

    disabled = tc.post("/api/settings/mcp", json=_sse("hyperv", False))
    assert disabled.status_code == 200
    disabled_body = disabled.json()
    assert disabled_body["status"] == "saved"
    assert disabled_body["mounted"] is False
    assert disabled_body.get("error") in (None, "")
    assert disabled_body["tools"] == []
    assert "hyperv" not in app.state.mcp_manager.get_mounted_servers()

    quiet = _row(tc.get("/api/settings/mcp").json(), "hyperv")
    assert quiet["enabled"] is False
    assert quiet["is_mounted"] is False
    assert quiet["tool_count"] == 0
    assert quiet["tools"] == []
    assert "mcp_hyperv_ping" not in _catalog_names(tc)
    stored = app.state.store.get_setting("mcp_servers")
    assert stored[0]["name"] == "hyperv"
    assert stored[0]["enabled"] is False

    again = tc.post("/api/settings/mcp", json=_sse("hyperv", True))
    assert again.status_code == 200
    assert again.json()["mounted"] is True
    remounted = _row(tc.get("/api/settings/mcp").json(), "hyperv")
    assert remounted["enabled"] is True
    assert remounted["is_mounted"] is True
    assert remounted["tools"] == ["mcp_hyperv_ping"]

    deleted = tc.delete("/api/settings/mcp/hyperv")
    assert deleted.status_code == 200
    assert tc.get("/api/settings/mcp").json() == []
    assert "hyperv" not in app.state.mcp_manager.get_mounted_servers()


def test_platform_disable_reports_still_mounted_when_unmount_fails(client):
    """Unmount failure stays visible. Happy path must not claim still mounted."""
    tc, app = client
    assert tc.post("/api/settings/mcp", json=_sse("hyperv", True)).status_code == 200

    real_unmount = app.state.mcp_manager.unmount_server

    async def refuse(_name):
        raise RuntimeError("unmount refused")

    app.state.mcp_manager.unmount_server = refuse
    disabled = tc.post("/api/settings/mcp", json=_sse("hyperv", False))
    app.state.mcp_manager.unmount_server = real_unmount
    assert disabled.status_code == 200
    body = disabled.json()
    assert body["mounted"] is True
    assert "unmount failed" in body["error"]
    assert "unmount refused" in body["error"]

    quiet = _row(tc.get("/api/settings/mcp").json(), "hyperv")
    assert quiet["enabled"] is False
    assert quiet["is_mounted"] is True
    assert quiet["tool_count"] == 1
    assert quiet["tools"] == ["mcp_hyperv_ping"]
    assert "mcp_hyperv_ping" in _catalog_names(tc)


def test_platform_enable_mount_failure_keeps_enabled_honest(client):
    """REQ-424-002: durable enabled stays true when mount fails."""
    tc, app = client
    saved = tc.post("/api/settings/mcp", json=_sse("hyperv", False))
    assert saved.status_code == 200
    assert saved.json()["mounted"] is False

    real_mount = app.state.mcp_manager.mount_server

    async def boom(**_kwargs):
        raise RuntimeError("handshake down")

    app.state.mcp_manager.mount_server = boom
    enabled = tc.post("/api/settings/mcp", json=_sse("hyperv", True))
    assert enabled.status_code == 200
    body = enabled.json()
    assert body["mounted"] is False
    assert "tool mounting failed" in body["error"]
    assert "handshake down" in body["error"]

    row = _row(tc.get("/api/settings/mcp").json(), "hyperv")
    assert row["enabled"] is True
    assert row["is_mounted"] is False
    assert row["tools"] == []
    assert row["tool_count"] == 0
    app.state.mcp_manager.mount_server = real_mount


def test_agent_disable_unmounts_that_server_only(client):
    """REQ-424-003: agent disable unmounts that server and leaves another mount alone."""
    tc, app = client
    platform = tc.post("/api/settings/mcp", json=_sse("keep-platform", True))
    assert platform.status_code == 200
    assert platform.json()["mounted"] is True

    created = tc.post(
        "/api/agents",
        json={
            "id": "hyperv",
            "name": "Hyper-V Specialist",
            "description": "Virtual machine manager",
            "system_prompt": "Manage Hyper-V infrastructure.",
        },
    )
    assert created.status_code == 200

    agent_on = tc.post("/api/agents/hyperv/mcp", json=_sse("agent-box", True))
    assert agent_on.status_code == 200
    assert agent_on.json()["mounted"] is True
    assert "mcp_agent-box_ping" in agent_on.json()["tools"]

    agent_off = tc.post("/api/agents/hyperv/mcp", json=_sse("agent-box", False))
    assert agent_off.status_code == 200
    off_body = agent_off.json()
    assert off_body["mounted"] is False
    assert off_body.get("error") in (None, "")
    assert off_body["tools"] == []

    agent_row = _row(tc.get("/api/agents/hyperv/mcp").json(), "agent-box")
    assert agent_row["enabled"] is False
    assert agent_row["is_mounted"] is False
    assert agent_row["tool_count"] == 0
    assert agent_row["tools"] == []
    assert "mcp_agent-box_ping" not in _catalog_names(tc)

    platform_row = _row(tc.get("/api/settings/mcp").json(), "keep-platform")
    assert platform_row["enabled"] is True
    assert platform_row["is_mounted"] is True
    assert platform_row["tools"] == ["mcp_keep-platform_ping"]
    assert "agent-box" not in app.state.mcp_manager.get_mounted_servers()
    assert "keep-platform" in app.state.mcp_manager.get_mounted_servers()

    agent_on_again = tc.post("/api/agents/hyperv/mcp", json=_sse("agent-box", True))
    assert agent_on_again.status_code == 200
    assert agent_on_again.json()["mounted"] is True
    remounted = _row(tc.get("/api/agents/hyperv/mcp").json(), "agent-box")
    assert remounted["enabled"] is True
    assert remounted["is_mounted"] is True
    assert "keep-platform" in app.state.mcp_manager.get_mounted_servers()
