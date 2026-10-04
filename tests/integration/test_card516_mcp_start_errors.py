"""
CARD-516: an MCP server that cannot start is reported as an error, not "ok" / "mounted (0 tools)".

Real stdio subprocesses: a command that dies on import, the raw fixture server
(good: two tools; empty: a working server with no tools).
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.mcp.client_adapter import MCPClientManager, MCPMountError
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app

RAW_SERVER = str(Path(__file__).resolve().parents[1] / "fixtures" / "mcp" / "raw_stdio_server.py")
BROKEN = [sys.executable, "-c", "import nonexistent_card516_mod"]
GOOD = [sys.executable, "-u", RAW_SERVER, "good"]
EMPTY = [sys.executable, "-u", RAW_SERVER, "empty"]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    store = SQLiteStateStore(db_path=str(tmp_path / "api.db"))
    store.initialize_db()
    return store, tmp_path


def _client(store, tmp_path):
    return TestClient(create_app(state_store=store, wiki_path=str(tmp_path / "wiki")))


def _row(rows, name):
    match = next((r for r in rows if r.get("name") == name), None)
    assert match is not None, name
    return match


@pytest.mark.asyncio
async def test_manager_refuses_to_mount_a_server_that_cannot_start():
    registry = ScopedToolRegistry()
    manager = MCPClientManager(tool_registry=registry)
    with pytest.raises(MCPMountError) as err:
        await manager.mount_server(name="c516", command=BROKEN)
    assert "nonexistent_card516_mod" in str(err.value)
    assert "c516" not in manager.get_mounted_servers()
    assert "nonexistent_card516_mod" in manager.get_mount_errors()["c516"]

    tools = await manager.mount_server(name="c516", command=GOOD)
    try:
        assert sorted(t.name for t in tools) == ["mcp_c516_lookup", "mcp_c516_ping"]
        assert manager.get_mount_errors() == {}
        assert registry.get_tool_definition("mcp_c516_ping") is not None
    finally:
        await manager.unmount_server("c516")


@pytest.mark.asyncio
async def test_a_working_server_with_no_tools_still_mounts():
    manager = MCPClientManager(tool_registry=ScopedToolRegistry())
    tools = await manager.mount_server(name="c516e", command=EMPTY)
    try:
        assert tools == []
        assert manager.get_mounted_servers()["c516e"]["tool_count"] == 0
        assert manager.get_mount_errors() == {}
    finally:
        await manager.unmount_server("c516e")


def test_settings_test_reports_error_with_reason(env):
    store, tmp_path = env
    with _client(store, tmp_path) as tc:
        bad = tc.post("/api/settings/mcp/test", json={"name": "c516", "command": BROKEN}).json()
        assert bad["status"] == "error"
        assert "nonexistent_card516_mod" in bad["error"]

        good = tc.post("/api/settings/mcp/test", json={"name": "c516", "command": GOOD}).json()
        assert good["status"] == "ok"
        assert good["tools_count"] == 2


def test_settings_save_keeps_config_but_reports_not_mounted(env):
    store, tmp_path = env
    with _client(store, tmp_path) as tc:
        saved = tc.post("/api/settings/mcp", json={"name": "c516", "command": BROKEN, "enabled": True}).json()
        assert saved["status"] == "saved"
        assert saved["mounted"] is False
        assert "nonexistent_card516_mod" in saved["error"]
        assert "nonexistent_card516_mod" in saved["last_error"]

        row = _row(tc.get("/api/settings/mcp").json(), "c516")
        assert row["is_mounted"] is False
        assert row["command"] == BROKEN  # operator-owned config is kept
        assert "nonexistent_card516_mod" in row["last_error"]

        fixed = tc.post("/api/settings/mcp", json={"name": "c516", "command": GOOD, "enabled": True}).json()
        try:
            assert fixed["mounted"] is True
            assert fixed["tools_count"] == 2
            row = _row(tc.get("/api/settings/mcp").json(), "c516")
            assert row["is_mounted"] is True
            assert row["last_error"] is None
        finally:
            tc.delete("/api/settings/mcp/c516")


def test_disabling_a_failed_server_clears_its_error(env):
    store, tmp_path = env
    with _client(store, tmp_path) as tc:
        tc.post("/api/settings/mcp", json={"name": "c516", "command": BROKEN, "enabled": True})
        tc.post("/api/settings/mcp", json={"name": "c516", "command": BROKEN, "enabled": False})
        row = _row(tc.get("/api/settings/mcp").json(), "c516")
        assert row["enabled"] is False
        assert row["last_error"] is None


def test_startup_auto_mount_failure_shows_in_the_list(env):
    store, tmp_path = env
    store.set_setting("mcp_servers", [{"name": "c516boot", "command": BROKEN, "enabled": True}])
    with _client(store, tmp_path) as tc:
        row = _row(tc.get("/api/settings/mcp").json(), "c516boot")
        assert row["is_mounted"] is False
        assert "nonexistent_card516_mod" in row["last_error"]


def test_agent_test_and_save_report_the_start_error(env):
    store, tmp_path = env
    with _client(store, tmp_path) as tc:
        bad = tc.post("/api/agents/autoreiv/mcp/test", json={"name": "c516a", "command": BROKEN}).json()
        assert bad["status"] == "error"
        assert "nonexistent_card516_mod" in bad["error"]

        saved = tc.post("/api/agents/autoreiv/mcp", json={"name": "c516a", "command": BROKEN, "enabled": True}).json()
        assert saved["mounted"] is False
        assert "nonexistent_card516_mod" in saved["last_error"]
        row = _row(tc.get("/api/agents/autoreiv/mcp").json(), "c516a")
        assert row["is_mounted"] is False
        assert "nonexistent_card516_mod" in row["last_error"]
        tc.delete("/api/agents/autoreiv/mcp/c516a")
