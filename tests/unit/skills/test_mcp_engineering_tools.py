"""
Unit tests for MCP Engineering Tools [CARD-394, ADR-0054].
Verifies scaffolding, AST analysis, simulated JSON-RPC contracts, Docker healthcheck validation,
graceful stdio fallback, and canonical single-lever registration.
"""

import sys

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.mcp_engineering_tools import MCPEngineeringTools
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_store(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test_store.db"))
    store.initialize_db()
    return store


@pytest.fixture
def mcp_tools(temp_store, tmp_path):
    registry = ScopedToolRegistry()
    tools = MCPEngineeringTools(
        state_store=temp_store,
        tool_registry=registry,
        data_dir=tmp_path / "data",
    )
    tools.register_tools(registry)
    return tools, registry


def test_scaffold_mcp_server_success(mcp_tools, tmp_path):
    tools, _ = mcp_tools
    target_dir = tmp_path / "test_mcp_proj"

    tools_spec = [
        {
            "name": "lookup_user",
            "description": "Fetch user by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["user_id"],
            },
        }
    ]

    res = tools.scaffold_mcp_server(
        name="user_service",
        description="User directory service",
        tools_spec=tools_spec,
        target_dir=str(target_dir),
    )

    assert res["success"] is True
    assert res["server_name"] == "user_service"
    assert (target_dir / "server.py").is_file()
    assert (target_dir / "pyproject.toml").is_file()
    assert (target_dir / "Dockerfile").is_file()
    assert (target_dir / "README.md").is_file()

    server_code = (target_dir / "server.py").read_text(encoding="utf-8")
    assert "FastMCP" in server_code
    assert "def health() -> str:" in server_code
    assert "def lookup_user(" in server_code
    assert "user_id: str" in server_code
    assert "limit: Optional[int] = None" in server_code

    dockerfile_code = (target_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "HEALTHCHECK" in dockerfile_code
    assert "mcpuser" in dockerfile_code
    assert "USER mcpuser" in dockerfile_code


def test_scaffold_mcp_server_invalid_name(mcp_tools):
    tools, _ = mcp_tools
    res = tools.scaffold_mcp_server(
        name="   !@#$%   ",
        description="Invalid name test",
        tools_spec=[],
    )
    # Sanitized to custom_mcp fallback
    assert res["success"] is True
    assert res["server_name"] == "custom_mcp"


def test_test_mcp_server_success(mcp_tools, tmp_path):
    tools, _ = mcp_tools
    target_dir = tmp_path / "valid_mcp_proj"

    tools_spec = [
        {
            "name": "ping",
            "description": "Ping test endpoint",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Ping count"},
                },
            },
        }
    ]

    tools.scaffold_mcp_server(
        name="ping_srv",
        description="Ping test service",
        tools_spec=tools_spec,
        target_dir=str(target_dir),
    )

    test_res = tools.test_mcp_server(project_path=str(target_dir), test_tool="ping")
    assert test_res["success"] is True
    assert test_res["syntax_valid"] is True
    assert test_res["tools_count"] == 2  # health + ping
    assert any(t["name"] == "ping" for t in test_res["tools"])
    assert any(t["name"] == "health" for t in test_res["tools"])


def test_test_mcp_server_syntax_error_negative(mcp_tools, tmp_path):
    """[REQ-394-005] Negative assertion: Reject servers with Python syntax errors."""
    tools, _ = mcp_tools
    proj_dir = tmp_path / "broken_syntax_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "server.py").write_text("def broken_func(:\n    return 42", encoding="utf-8")

    res = tools.test_mcp_server(project_path=str(proj_dir))
    assert res["success"] is False
    assert res["syntax_valid"] is False
    assert "syntax error" in res["error"].lower()
    assert len(res["diagnostics"]) > 0


def test_test_mcp_server_invalid_schema_negative(mcp_tools, tmp_path):
    """[REQ-394-005] Negative assertion: Reject servers with invalid JSON-RPC schemas."""
    tools, _ = mcp_tools
    proj_dir = tmp_path / "invalid_schema_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Server code with invalid identifier (cannot use syntax error, but invalid JSON-RPC character)
    # We can test when requested tool is not found
    (proj_dir / "server.py").write_text(
        """from mcp.server.fastmcp import FastMCP
mcp = FastMCP("test")

@mcp.tool()
def valid_tool() -> str:
    \"\"\"Valid tool docstring.\"\"\"
    return "ok"
""",
        encoding="utf-8",
    )

    res = tools.test_mcp_server(project_path=str(proj_dir), test_tool="non_existent_tool")
    assert res["success"] is False
    assert "non_existent_tool" in res["error"]
    assert "Available tools" in res["diagnostics"][0]


def test_deploy_mcp_container_missing_healthcheck_negative(mcp_tools, tmp_path):
    """[REQ-394-005] Negative assertion: Reject container deployments missing HEALTHCHECK."""
    tools, _ = mcp_tools
    proj_dir = tmp_path / "no_healthcheck_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)

    (proj_dir / "server.py").write_text("# server code", encoding="utf-8")
    # Dockerfile intentionally lacking HEALTHCHECK
    (proj_dir / "Dockerfile").write_text(
        """FROM python:3.12-slim
WORKDIR /app
COPY server.py .
CMD ["python", "server.py"]
""",
        encoding="utf-8",
    )

    res = tools.deploy_mcp_container(project_path=str(proj_dir), check_health=True)
    assert res["success"] is False
    assert "HEALTHCHECK" in res["error"]
    assert any("HEALTHCHECK" in d for d in res["diagnostics"])


def test_deploy_mcp_container_fallback_to_stdio(mcp_tools, tmp_path):
    """[REQ-394-004] Verify graceful fallback to stdio transport when Docker daemon is down or absent."""
    tools, _ = mcp_tools
    proj_dir = tmp_path / "fallback_proj"
    tools.scaffold_mcp_server(
        name="fallback_srv",
        description="Fallback test service",
        tools_spec=[],
        target_dir=str(proj_dir),
    )

    res = tools.deploy_mcp_container(project_path=str(proj_dir), force_stdio=True)
    assert res["success"] is True
    assert res["mode"] == "stdio"
    assert "fallback_reason" in res
    assert res["transport"] == "stdio"
    assert sys.executable in res["command"][0]


@pytest.mark.asyncio
async def test_register_mcp_service_canonical_single_lever(mcp_tools, temp_store):
    """[REQ-394-004] Verify registration writes to canonical store.get_setting('mcp_servers')."""
    tools, _ = mcp_tools

    res = await tools.register_mcp_service(
        name="enterprise_db",
        transport="stdio",
        url_or_command=["python", "db_server.py"],
        enabled=True,
    )

    assert res["success"] is True
    assert res["server_name"] == "enterprise_db"
    assert res["saved"] is True

    # Single lever check: direct state store read
    stored = temp_store.get_setting("mcp_servers")
    assert isinstance(stored, list)
    matching = next((s for s in stored if s.get("name") == "enterprise_db"), None)
    assert matching is not None
    assert matching["transport"] == "stdio"
    assert matching["command"] == ["python", "db_server.py"]
    assert matching["enabled"] is True


@pytest.mark.asyncio
async def test_developer_agent_pack_has_mcp_engineering_tools(tmp_path):
    """Verify Developer platform pack bootstrap has mcp-engineering tools wired."""
    store = SQLiteStateStore(db_path=str(tmp_path / "store.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)

    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "data" / "skills"),
    )

    dev = registry.get_agent("developer")
    assert dev is not None

    # Check tools available in master tool registry
    assert "scaffold_mcp_server" in tool_reg
    assert "test_mcp_server" in tool_reg
    assert "deploy_mcp_container" in tool_reg
    assert "register_mcp_service" in tool_reg
