"""
End-to-End Integration tests for CARD-392: AutoReiv Cross-Instance Federation.
Verifies that one AutoReiv instance (client) can mount a peer AutoReiv instance
(hosted MCP server) over HTTP/SSE, discover agent dispatchers and passive tools,
author a companion SKILL.md runbook, and execute federated tool calls.
"""

from unittest.mock import AsyncMock

import httpx
import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.mcp.client_adapter import MCPClientManager
from src.infrastructure.mcp.companion_author import author_mcp_companion_skill
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def federation_cluster(tmp_path):
    # Host (Homelab instance) setup
    host_store = SQLiteStateStore(db_path=":memory:")
    host_store.initialize_db()
    host_wiki = tmp_path / "host_wiki"
    host_wiki.mkdir(parents=True)
    (host_wiki / "Cluster.md").write_text("# Homelab Cluster\nNodes: 3, Status: Healthy.", encoding="utf-8")

    host_app = create_app(
        state_store=host_store,
        wiki_path=str(host_wiki),
    )

    # Client (Workstation instance) setup
    client_reg = ScopedToolRegistry()
    client_mcp_mgr = MCPClientManager(tool_registry=client_reg)
    client_data_dir = tmp_path / "client_data"
    client_data_dir.mkdir(parents=True)

    return {
        "host_app": host_app,
        "host_store": host_store,
        "client_mcp_mgr": client_mcp_mgr,
        "client_reg": client_reg,
        "client_data_dir": client_data_dir,
    }


@pytest.mark.asyncio
async def test_autoreiv_federation_mount_discover_and_execute(federation_cluster):
    """
    E2E Federation Flow:
    1. Client mounts host via ASGITransport to /api/mcp/messages.
    2. Host publishes agent dispatchers and passive tools.
    3. Client discovers tools and authors companion SKILL.md runbook.
    4. Client executes passive tool (read_wiki_document) against host.
    5. Client executes agent dispatcher (ask_developer) against host.
    6. Client unmounts server cleanly.
    """
    host_app = federation_cluster["host_app"]
    client_mcp_mgr = federation_cluster["client_mcp_mgr"]
    client_reg = federation_cluster["client_reg"]
    client_data_dir = federation_cluster["client_data_dir"]

    # Mock host developer agent execution
    host_kernel = host_app.state.kernel
    host_kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content="Federated Developer: Node 1 memory verified at 85% headroom.",
        )
    )

    # 1. Mount host as remote MCP server 'homelab'
    transport = httpx.ASGITransport(app=host_app)
    tools = await client_mcp_mgr.mount_server(
        name="homelab",
        transport="sse",
        url="http://testserver/api/mcp/messages",
        _http_transport=transport,
    )

    tool_names = [t.name for t in tools]
    assert "mcp_homelab_ask_developer" in tool_names
    assert "mcp_homelab_ask_autoreiv" in tool_names
    assert "mcp_homelab_read_wiki_document" in tool_names
    assert "mcp_homelab_get_system_health" in tool_names

    # 2. Author companion SKILL.md runbook
    skill_file = author_mcp_companion_skill(
        server_name="homelab",
        tools=tools,
        url="http://homelab:8000/api/mcp/sse",
        data_dir=client_data_dir,
    )
    assert skill_file is not None
    assert skill_file.is_file()
    skill_content = skill_file.read_text(encoding="utf-8")
    assert "Homelab Remote MCP Capabilities" in skill_content
    assert "mcp_homelab_ask_developer" in skill_content

    # 3. Call passive tool via client tool registry dispatch handler
    assert "mcp_homelab_read_wiki_document" in client_reg._tools
    read_wiki_handler = client_reg._tools["mcp_homelab_read_wiki_document"].handler

    result = await read_wiki_handler(path="Cluster.md")
    assert result["success"] is True
    assert "Homelab Cluster" in result["output"]
    assert "Nodes: 3, Status: Healthy" in result["output"]

    # 4. Call agent dispatcher tool via client tool registry dispatch handler
    assert "mcp_homelab_ask_developer" in client_reg._tools
    ask_dev_handler = client_reg._tools["mcp_homelab_ask_developer"].handler

    agent_result = await ask_dev_handler(prompt="Check node memory", session_id="workstation-turn-1")
    assert agent_result["success"] is True
    assert "Federated Developer: Node 1 memory verified" in agent_result["output"]

    # 5. Clean unmount
    await client_mcp_mgr.unmount_server("homelab")
    assert "mcp_homelab_read_wiki_document" not in client_reg._tools
    assert "mcp_homelab_ask_developer" not in client_reg._tools
