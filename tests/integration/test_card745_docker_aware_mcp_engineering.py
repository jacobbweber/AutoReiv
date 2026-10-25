"""CARD-745: Operator contract for Docker- and host-aware MCP engineering, container deployment, and immediate session mounting."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.skills.mcp_engineering_tools import MCPEngineeringTools
from src.application.skills.session_skills import (
    clear_session_skill_activations,
    resolve_turn_active_tools,
)
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_card745_dockerfile_and_compose_include_docker_cli_and_socket():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    svc = compose["services"]["autoreiv"]

    assert "/usr/local/bin/docker" in dockerfile
    assert "AUTOREIV_PROJECTS_HOST_PATH=${AUTOREIV_PROJECTS_HOST_PATH:-}" in svc["environment"]
    assert "/var/run/docker.sock:/var/run/docker.sock" in svc["volumes"]


@pytest.mark.asyncio
async def test_card745_scaffold_defaults_to_projects_dir_and_executes_custom_tool_code(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    projects_dir = tmp_path / "projects"
    host_dir = tmp_path / "host_mount"
    host_dir.mkdir(parents=True, exist_ok=True)
    (host_dir / "alpha.txt").write_text("alpha", encoding="utf-8")
    (host_dir / "beta_dir").mkdir(exist_ok=True)

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(projects_dir))
    clear_session_skill_activations()

    store = SQLiteStateStore(db_path=str(data_dir / "autoreiv.db"))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(data_dir / "wiki"),
        skills_dir=str(data_dir / "skills"),
    )

    mcp_tools = registry.mcp_engineering_tools
    assert mcp_tools is not None

    # 1. Scaffold without target_dir -> defaults to $AUTOREIV_PROJECTS_DIR/<name>, NOT scratch/mcp_servers
    scaffold_res = mcp_tools.scaffold_mcp_server(
        name="host_fs_mcp",
        description="Host directory inspector MCP server",
        tools_spec=[
            {
                "name": "list_host_dir",
                "description": "List entries in a directory on the host.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list"},
                    },
                    "required": ["path"],
                },
                "code": (
                    "target = Path(path)\n"
                    "if not target.is_dir():\n"
                    "    return f'Not a directory: {path}'\n"
                    "return ', '.join(sorted(p.name for p in target.iterdir()))"
                ),
            }
        ],
    )
    assert scaffold_res["success"] is True
    expected_project_dir = (projects_dir / "host_fs_mcp").resolve()
    assert Path(scaffold_res["project_path"]).resolve() == expected_project_dir
    assert "scratch/mcp_servers" not in scaffold_res["project_path"]

    # 2. AST & JSON-RPC schema check passes
    test_res = mcp_tools.test_mcp_server(project_path=str(expected_project_dir), test_tool="list_host_dir")
    assert test_res["success"] is True
    assert test_res["tools_count"] == 2

    # 3. Real stdio registration and live execution of custom tool code (without needing external mcp package!)
    session_id = "sess_card745"
    token = _tool_context.set({"agent_id": "autoreiv", "session_id": session_id})
    try:
        reg_res = await mcp_tools.register_mcp_service(
            name="host_fs_mcp",
            transport="stdio",
            url_or_command=[sys.executable, str(expected_project_dir / "server.py")],
            sample_tool="list_host_dir",
            sample_arguments={"path": str(host_dir)},
        )
    finally:
        _tool_context.reset(token)
    assert reg_res["success"] is True, reg_res
    assert reg_res["mounted"] is True
    assert "mcp_host_fs_mcp_list_host_dir" in reg_res["tools"]
    assert reg_res.get("companion_skill_id") == "mcp-host_fs_mcp"

    # 4. Immediate session mounting: resolve_turn_active_tools includes mcp_host_fs_mcp_list_host_dir right away
    autoreiv = registry.get_agent("autoreiv")
    allowed = resolve_allowed_tools(autoreiv)
    assert "mcp_host_fs_mcp_list_host_dir" in allowed

    active_tools = resolve_turn_active_tools(
        tool_reg,
        autoreiv,
        session_id=session_id,
        history=[],
    )
    active_names = {t.name for t in active_tools}
    assert "mcp_host_fs_mcp_list_host_dir" in active_names

    # 5. Execute the mounted MCP tool and verify custom tool code output
    tool_def = tool_reg.get_tool_definition("mcp_host_fs_mcp_list_host_dir")
    assert tool_def is not None
    call_res = await tool_reg._tools["mcp_host_fs_mcp_list_host_dir"].handler(path=str(host_dir))
    output_text = str(call_res)
    assert "alpha.txt" in output_text
    assert "beta_dir" in output_text


def test_card745_deploy_mcp_container_translates_host_volumes_and_returns_docker_internal_url(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "docker")
    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", "/data/projects")
    monkeypatch.setenv("AUTOREIV_PROJECTS_HOST_PATH", "/home/spark/projects")

    store = SQLiteStateStore(db_path=str(tmp_path / "store.db"))
    store.initialize_db()
    tools = MCPEngineeringTools(
        state_store=store,
        tool_registry=ScopedToolRegistry(state_store=store),
        data_dir=tmp_path / "data",
    )

    proj_dir = tmp_path / "host_mcp"
    tools.scaffold_mcp_server(
        name="host_mcp",
        description="Host MCP",
        tools_spec=[{"name": "ping", "description": "Ping"}],
        target_dir=str(proj_dir),
    )

    recorded_cmds: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        recorded_cmds.append(list(cmd))
        res = MagicMock()
        res.returncode = 0
        res.stdout = "abc123def456\n"
        res.stderr = ""
        return res

    with patch("shutil.which", return_value="/usr/local/bin/docker"), patch("subprocess.run", side_effect=fake_run):
        deploy_res = tools.deploy_mcp_container(
            project_path=str(proj_dir),
            port=8765,
            volumes=["/data/projects/host_mcp/shared:/shared:ro", "/home/spark:/host:ro"],
            env_vars={"HOST_ROOT": "/host"},
        )

    assert deploy_res["success"] is True
    assert deploy_res["mode"] == "docker"
    assert deploy_res["url"] == "http://host.docker.internal:8765/sse"

    run_cmds = [c for c in recorded_cmds if len(c) >= 2 and c[1] == "run"]
    assert len(run_cmds) == 1
    run_cmd = run_cmds[0]
    assert "/home/spark/projects/host_mcp/shared:/shared:ro" in run_cmd
    assert "/home/spark:/host:ro" in run_cmd
    assert "MCP_TRANSPORT=sse" in run_cmd
    assert "HOST_ROOT=/host" in run_cmd
