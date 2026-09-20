"""
Unit and integration tests for CARD-392: AutoReiv Hosted MCP Server & Cross-Instance Federation.
Verifies:
- [REQ-392-001]: Inbound MCP Server-Sent Events (SSE) stream endpoint at /api/mcp/sse.
- [REQ-392-002]: JSON-RPC tools/list returns agent dispatchers (ask_<agent_id>) and passive tools.
- [REQ-392-003]: JSON-RPC tools/call invokes AgentKernel.run_turn for agent dispatchers.
- [REQ-392-004]: Hosted MCP status and authentication token enforcement.
- [REQ-392-005]: Negative assertion: Local agent turns execute tools in-process without network hops to /api/mcp/sse.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, CompletionResponse, Role, ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def app_and_client(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(parents=True)
    (wiki_dir / "Architecture.md").write_text("# AutoReiv Architecture\nLocal-first AI OS.", encoding="utf-8")

    app = create_app(
        state_store=store,
        wiki_path=str(wiki_dir),
    )

    with TestClient(app) as client:
        yield app, client


def test_hosted_mcp_sse_handshake_endpoint(app_and_client):
    """GET /api/mcp/sse returns SSE stream with initial endpoint event [REQ-392-001]."""
    app, client = app_and_client

    with client.stream("GET", "/api/mcp/sse?handshake_only=true") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Read first SSE event
        lines = []
        for line in response.iter_lines():
            if line:
                lines.append(line)
            if len(lines) >= 2:
                break

        assert "event: endpoint" in lines[0]
        assert "data: /api/mcp/messages?session_id=" in lines[1]


def test_hosted_mcp_initialize_and_ping(app_and_client):
    """POST /api/mcp/messages handles initialize handshake and ping [REQ-392-002]."""
    app, client = app_and_client

    # 1. Initialize
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "TestClient", "version": "1.0.0"},
        },
    }
    res = client.post("/api/mcp/messages", json=init_msg)
    assert res.status_code == 200
    data = res.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert data["result"]["protocolVersion"] == "2024-11-05"
    assert data["result"]["serverInfo"]["name"] == "AutoReiv Hosted MCP Server"

    # 2. Ping
    ping_msg = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    res_ping = client.post("/api/mcp/messages", json=ping_msg)
    assert res_ping.status_code == 200
    assert res_ping.json()["result"] == {}


def test_hosted_mcp_tools_list_publishes_agents_and_passive_tools(app_and_client):
    """POST /api/mcp/messages tools/list publishes chat-visible agents and passive lookups [REQ-392-002]."""
    app, client = app_and_client

    msg = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/list",
    }
    res = client.post("/api/mcp/messages", json=msg)
    assert res.status_code == 200
    data = res.json()
    tools = data["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    # Verify Agent Dispatchers are present
    assert "ask_autoreiv" in tool_names
    assert "ask_developer" in tool_names
    assert "ask_tutor" in tool_names

    # Verify Safe Passive Tools are present
    assert "search_wiki" in tool_names
    assert "read_wiki_document" in tool_names
    assert "get_system_health" in tool_names

    # Negative assertion: Retired or non-autonomous engines are NOT published
    assert "ask_direct" not in tool_names
    assert "ask_coding" not in tool_names
    assert "ask_agent_builder" not in tool_names
    assert "ask_assistant" not in tool_names


def test_hosted_mcp_tools_call_agent_dispatcher(app_and_client):
    """POST /api/mcp/messages tools/call ask_developer executes turn via AgentKernel [REQ-392-003]."""
    app, client = app_and_client

    # Mock kernel.run_turn
    mock_response = ChatMessage(
        role=Role.ASSISTANT,
        content="Developer verified test suites: 4 passed, 0 failed.",
    )
    app.state.kernel.run_turn = AsyncMock(return_value=mock_response)

    call_msg = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/call",
        "params": {
            "name": "ask_developer",
            "arguments": {
                "prompt": "Run full test suite",
                "session_id": "test-remote-session",
            },
        },
    }
    res = client.post("/api/mcp/messages", json=call_msg)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 20
    assert data["result"]["isError"] is False
    content_list = data["result"]["content"]
    assert len(content_list) == 1
    assert "Developer verified test suites" in content_list[0]["text"]

    # Verify AgentKernel.run_turn arguments
    app.state.kernel.run_turn.assert_called_once()
    call_kwargs = app.state.kernel.run_turn.call_args.kwargs
    assert call_kwargs["agent"].id == "developer"
    assert call_kwargs["user_content"] == "Run full test suite"
    assert call_kwargs["session_id"] == "test-remote-session"


def test_hosted_mcp_tools_call_passive_wiki_and_health(app_and_client):
    """POST /api/mcp/messages tools/call passive tools execute immediately [REQ-392-003]."""
    app, client = app_and_client

    # 1. read_wiki_document
    read_msg = {
        "jsonrpc": "2.0",
        "id": 30,
        "method": "tools/call",
        "params": {
            "name": "read_wiki_document",
            "arguments": {"path": "Architecture.md"},
        },
    }
    res = client.post("/api/mcp/messages", json=read_msg)
    assert res.status_code == 200
    data = res.json()
    assert data["result"]["isError"] is False
    assert "AutoReiv Architecture" in data["result"]["content"][0]["text"]

    # 2. get_system_health
    health_msg = {
        "jsonrpc": "2.0",
        "id": 31,
        "method": "tools/call",
        "params": {"name": "get_system_health", "arguments": {}},
    }
    res_health = client.post("/api/mcp/messages", json=health_msg)
    assert res_health.status_code == 200
    health_data = res_health.json()["result"]["content"][0]["text"]
    assert "AutoReiv Hosted MCP Server" in health_data

    # 3. Unknown tool returns error payload
    unknown_msg = {
        "jsonrpc": "2.0",
        "id": 32,
        "method": "tools/call",
        "params": {"name": "unknown_tool", "arguments": {}},
    }
    res_unknown = client.post("/api/mcp/messages", json=unknown_msg)
    assert res_unknown.status_code == 200
    assert res_unknown.json()["result"]["isError"] is True


def test_hosted_mcp_auth_token_protection(app_and_client):
    """Token authentication protects inbound MCP endpoints when configured [REQ-392-004]."""
    app, client = app_and_client

    # Configure auth token in store
    app.state.store.set_setting("hosted_mcp", {"api_token": "secret-federation-token"})

    # 1. Missing token -> 401
    init_msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    res_unauth = client.post("/api/mcp/messages", json=init_msg)
    assert res_unauth.status_code == 401

    # 2. Valid Bearer token -> 200
    res_auth = client.post(
        "/api/mcp/messages",
        json=init_msg,
        headers={"Authorization": "Bearer secret-federation-token"},
    )
    assert res_auth.status_code == 200

    # 3. Valid x-api-key -> 200
    res_key = client.post(
        "/api/mcp/messages",
        json=init_msg,
        headers={"x-api-key": "secret-federation-token"},
    )
    assert res_key.status_code == 200


def test_hosted_mcp_status_endpoint(app_and_client):
    """GET /api/mcp/status reports server health and published agents [REQ-392-004]."""
    app, client = app_and_client

    res = client.get("/api/mcp/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"
    assert data["hosted_server"]["endpoint"] == "/api/mcp/sse"
    assert "developer" in data["hosted_server"]["published_agents"]
    assert "autoreiv" in data["hosted_server"]["published_agents"]


@pytest.mark.asyncio
async def test_local_agent_turn_never_calls_hosted_mcp_endpoint(app_and_client):
    """
    Negative assertion [REQ-392-005]:
    Local agent turn execution routes directly in-process and never makes loopback HTTP calls to /api/mcp/sse.
    """
    app, client = app_and_client
    kernel = app.state.kernel

    dev_agent = AgentProfile(
        id="developer",
        name="Developer",
        description="Lead Software Engineer",
        system_prompt="You are a developer.",
        allowed_tool_names=["read_wiki_document"],
    )

    step1 = ChatMessage(
        role=Role.ASSISTANT,
        content="Reading docs",
        tool_calls=[ToolCall(id="call_1", name="read_wiki_document", arguments={"path": "Architecture.md"})],
    )
    step2 = ChatMessage(
        role=Role.ASSISTANT,
        content="I have read the architecture document in-process.",
    )
    resp1 = CompletionResponse(model="mock-model", message=step1)
    resp2 = CompletionResponse(model="mock-model", message=step2)
    kernel.gateway.complete = AsyncMock(side_effect=[resp1, resp2])

    with patch("httpx.AsyncClient.post") as mock_http_post:
        # Mock tool handler execution in-process
        chat_msg = await kernel.run_turn(
            agent=dev_agent,
            session_id="local-inprocess-test",
            user_content="Inspect documentation",
            save_to_history=False,
            approval_mode="auto",
        )

        assert chat_msg is not None
        assert "architecture" in chat_msg.content.lower()
        # Assert ZERO HTTP post network calls were made to /api/mcp/sse or any loopback
        mock_http_post.assert_not_called()
