"""
Integration tests for MCP Server Engineering & Deployment Lifecycle [CARD-394, ADR-0054].
Tests the full lifecycle: scaffold -> test -> deploy fallback -> canonical registration -> companion SKILL.md.
"""

from unittest.mock import AsyncMock

import pytest

from src.application.skills.mcp_engineering_tools import MCPEngineeringTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolDefinition
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.mark.asyncio
async def test_mcp_dev_deploy_lifecycle_end_to_end(tmp_path):
    data_dir = tmp_path / "user_data"
    skills_dir = data_dir / "skills"
    project_root = tmp_path / "scratch" / "cluster_service"

    store = SQLiteStateStore(db_path=str(tmp_path / "autoreiv.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)

    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(skills_dir),
    )

    # Mock MCPClientManager to simulate live mounting
    mock_mcp_manager = AsyncMock()
    mock_mcp_manager.mount_server.return_value = [
        ToolDefinition(name="mcp_cluster_service_health", description="Health check endpoint", parameters={}),
        ToolDefinition(name="mcp_cluster_service_restart_node", description="Restart node", parameters={"properties": {"node_id": {"type": "string"}}}),
    ]

    mcp_tools = MCPEngineeringTools(
        state_store=store,
        mcp_manager=mock_mcp_manager,
        tool_registry=tool_reg,
        data_dir=data_dir,
    )

    # 1. Scaffold MCP Server
    tools_spec = [
        {
            "name": "restart_node",
            "description": "Restart cluster node",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node to restart"},
                },
                "required": ["node_id"],
            },
        }
    ]

    scaffold_res = mcp_tools.scaffold_mcp_server(
        name="cluster_service",
        description="Cluster infrastructure operations",
        tools_spec=tools_spec,
        target_dir=str(project_root),
    )
    assert scaffold_res["success"] is True
    assert (project_root / "server.py").is_file()
    assert (project_root / "Dockerfile").is_file()
    assert (project_root / "pyproject.toml").is_file()
    assert (project_root / "README.md").is_file()

    # 2. Test MCP Server
    test_res = mcp_tools.test_mcp_server(
        project_path=str(project_root),
        test_tool="restart_node",
    )
    assert test_res["success"] is True
    assert test_res["syntax_valid"] is True
    assert test_res["tools_count"] == 2

    # 3. Deploy MCP Container (gracefully falls back to stdio if docker daemon absent or force_stdio)
    deploy_res = mcp_tools.deploy_mcp_container(
        project_path=str(project_root),
        check_health=True,
        force_stdio=True,
    )
    assert deploy_res["success"] is True
    assert deploy_res["mode"] == "stdio"

    # 4. Canonical Single-Lever Registration
    reg_res = await mcp_tools.register_mcp_service(
        name="cluster_service",
        transport="stdio",
        url_or_command=["python", str(project_root / "server.py")],
        enabled=True,
    )
    assert reg_res["success"] is True
    assert reg_res["saved"] is True
    assert reg_res["mounted"] is True
    assert reg_res["tool_count"] == 2
    assert reg_res["companion_skill_written"] is True

    # 5. Single Lever Assertion: Check SQLite State Store
    servers = store.get_setting("mcp_servers")
    assert isinstance(servers, list)
    matching = next((s for s in servers if s.get("name") == "cluster_service"), None)
    assert matching is not None
    assert matching["enabled"] is True

    # 6. Companion SKILL.md Assertion
    companion_skill = data_dir / "skills" / "mcp-cluster_service" / "SKILL.md"
    assert companion_skill.is_file()
    skill_content = companion_skill.read_text(encoding="utf-8")
    assert "Cluster Service" in skill_content
    assert "mcp_cluster_service_restart_node" in skill_content

    # 7. Agent Authorization Verification
    dev = registry.get_agent("developer")
    assert dev is not None
    # Developer pack has mcp-engineering in allowed_skill
    assert "mcp-engineering" in dev.allowed_skill or "mcp-engineering" in (dev.pack_tool_names or [])
