"""Unit tests for standalone Remote MCP Server scaffolding and packaging [CARD-184]."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase, _scaffold_mcp_server
from src.application.agent_training_factory.phases.scenario_verify import _tool_code_corpus
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def factory_repo():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    store = SQLiteStateStore(db_path=path)
    store.initialize_db()
    yield FactoryPacketRepository(store)
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.mark.asyncio
async def test_author_phase_scaffolds_mcp_package_with_zero_loose_tools(factory_repo):
    job = FactoryJob(
        id="job_mcp_test_01",
        session_id="sess_test",
        target_agent_id="hyperv",
        seed_intent="Manage Hyper-V VMs and checkpoints",
        objectives=["Inspect VM status", "Create recovery checkpoints"],
        current_node_id="author",
    )
    factory_repo.save_job(job)

    # Initial blueprint packet declaring deliverable_type = "mcp"
    bp_packet = FactoryPacket(
        job_id=job.id,
        packet_type="gap",
        sender_role="blueprint",
        recipient_role="author",
        node_id="blueprint",
        payload={
            "blueprint": {
                "deliverable_type": "mcp",
                "skills": [
                    {
                        "id": "hyperv-vm-lifecycle",
                        "name": "Hyper-V VM Lifecycle",
                        "description": "Manage VMs",
                        "tools": ["manage_hyperv_vm"],
                    }
                ],
                "tools": [
                    {
                        "name": "manage_hyperv_vm",
                        "actions": ["status", "list", "checkpoint"],
                        "description": "Dispatcher for Hyper-V VM lifecycle",
                        "deliverable_type": "mcp",
                    }
                ],
                "scenarios": [],
            }
        },
    )
    factory_repo.save_packet(bp_packet)

    ctx = PhaseContext(
        job=job,
        repo=factory_repo,
    )

    phase = AuthorPhase()
    res = await phase.run(ctx)
    assert res.outcome == "ok"

    files_map = res.artifacts["files_map"]

    # 1. MCP package files MUST be present
    required_mcp_files = [
        "mcp/server.py",
        "mcp/Dockerfile",
        "mcp/docker-compose.yml",
        "mcp/requirements.txt",
        "mcp/run.ps1",
        "mcp/run.sh",
        "mcp/README.md",
    ]
    for mcp_file in required_mcp_files:
        assert mcp_file in files_map, f"Expected {mcp_file} in files_map"
        assert len(files_map[mcp_file].strip()) > 10, f"{mcp_file} must not be empty"

    # 2. Strict constraint: ZERO loose tools files allowed under tools/
    loose_tools = [k for k in files_map if k.startswith("tools/")]
    assert loose_tools == [], f"Expected zero loose tools, found: {loose_tools}"

    # 3. Skills runbook must be present
    skill_files = [k for k in files_map if k.startswith("skills/")]
    assert len(skill_files) >= 1


def test_scaffolded_mcp_server_is_self_contained():
    tool_specs = [
        {
            "name": "manage_hyperv_vm",
            "actions": ["status", "list", "checkpoint"],
            "description": "Dispatcher for Hyper-V VM lifecycle",
        }
    ]
    server_code = _scaffold_mcp_server("hyperv", tool_specs, {})

    # Syntax valid
    tree = ast.parse(server_code)
    assert tree is not None

    # Zero internal AutoReiv dependencies
    assert "src.infrastructure" not in server_code
    assert "src.application" not in server_code
    assert "src.domain" not in server_code


def test_scaffolded_mcp_server_stdio_and_http_execution():
    tool_specs = [
        {
            "name": "manage_test_tool",
            "actions": ["status", "test_action"],
            "description": "Test tool dispatcher",
        }
    ]
    server_code = _scaffold_mcp_server("test_agent", tool_specs, {})

    with tempfile.TemporaryDirectory() as tmpdir:
        server_path = Path(tmpdir) / "server.py"
        server_path.write_text(server_code, encoding="utf-8")

        # 1. Test Stdio JSON-RPC Execution
        proc = subprocess.Popen(
            [sys.executable, str(server_path), "--mode", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            req = {"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            resp = json.loads(line)
            assert resp.get("id") == "1"
            tools = resp.get("result", {}).get("tools", [])
            assert any(t["name"] == "manage_test_tool" for t in tools)

            # Test tool call
            call_req = {
                "jsonrpc": "2.0",
                "id": "2",
                "method": "tools/call",
                "params": {"name": "manage_test_tool", "arguments": {"action": "status"}},
            }
            proc.stdin.write(json.dumps(call_req) + "\n")
            proc.stdin.flush()
            call_line = proc.stdout.readline()
            call_resp = json.loads(call_line)
            assert call_resp.get("id") == "2"
            content = call_resp.get("result", {}).get("content", [])
            assert len(content) > 0
        finally:
            proc.terminate()
            proc.wait(timeout=2.0)

        # 2. Test HTTP JSON-RPC Execution
        http_port = 18942
        http_proc = subprocess.Popen(
            [sys.executable, str(server_path), "--mode", "http", "--port", str(http_port), "--host", "127.0.0.1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            time.sleep(0.8)
            # Query tools/list via HTTP POST
            http_req_data = json.dumps({"jsonrpc": "2.0", "id": "http-1", "method": "tools/list", "params": {}}).encode("utf-8")
            http_req = urllib.request.Request(
                f"http://127.0.0.1:{http_port}/mcp",
                data=http_req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(http_req, timeout=3.0) as http_resp:
                assert http_resp.status == 200
                data = json.loads(http_resp.read().decode("utf-8"))
                assert data.get("id") == "http-1"
                tools = data.get("result", {}).get("tools", [])
                assert any(t["name"] == "manage_test_tool" for t in tools)
        finally:
            http_proc.terminate()
            http_proc.wait(timeout=2.0)


def test_scenario_verify_scans_mcp_server_corpus():
    files_map = {
        "mcp/server.py": "def manage_hyperv_vm(action='status'):\n    # Hyper-V\\Checkpoint-VM cmdlet\n    return {'checkpoint-vm': True}\n",
        "skills/hyperv/SKILL.md": "Hyper-V Skill Runbook",
    }
    corpus = _tool_code_corpus(files_map)
    assert "checkpoint-vm" in corpus


@pytest.mark.asyncio
async def test_verify_phase_runs_mcp_battery_without_synthesizing_tools(factory_repo):
    job = FactoryJob(
        id="job_verify_mcp_01",
        session_id="sess_test",
        target_agent_id="hyperv",
        seed_intent="Manage Hyper-V VMs and checkpoints",
        objectives=["Inspect VM status", "Create recovery checkpoints"],
        current_node_id="verify",
    )
    factory_repo.save_job(job)

    tool_specs = [
        {
            "name": "manage_hyperv_vm",
            "actions": ["status", "list", "checkpoint"],
            "description": "Dispatcher for Hyper-V VM lifecycle",
        }
    ]
    server_code = _scaffold_mcp_server("hyperv", tool_specs, {})
    skill_code = """---
name: hyperv-vm-lifecycle
description: "Hyper-V VM Lifecycle Automation"
tools: [manage_hyperv_vm]
---

# Hyper-V VM Lifecycle

## Purpose & Scope
Manage Hyper-V VMs and checkpoints.

### Objectives
- Inspect VM status
- Create recovery checkpoints

## Prerequisites & Tools
- Required Capabilities: `manage_hyperv_vm`

## Standard Operating Procedure (SOP)
- Step 1: Pre-flight check via manage_hyperv_vm(action="status")
- Step 2: Validate VM parameters
- Step 3: Call manage_hyperv_vm with intended action

## Available Actions
- `status`: Pre-flight inspection of Hyper-V VMs
- `list`: List all virtual machines
- `checkpoint`: Create recovery checkpoints

## Error Handling
- Capture exceptions and verify Hyper-V service status
"""

    author_packet = FactoryPacket(
        job_id=job.id,
        packet_type="work",
        sender_role="author",
        recipient_role="verify",
        node_id="author",
        payload={
            "tool_name": "manage_hyperv_vm",
            "tool_names": ["manage_hyperv_vm"],
            "files_map": {
                "mcp/server.py": server_code,
                "skills/hyperv-vm-lifecycle/SKILL.md": skill_code,
            },
        },
    )
    factory_repo.save_packet(author_packet)

    ctx = PhaseContext(job=job, repo=factory_repo)
    from src.application.agent_training_factory.phases.verify import VerifyPhase

    phase = VerifyPhase()
    res = await phase.run(ctx)
    assert res.outcome == "ok", f"Outcome={res.outcome}, Msg={res.message}, Artifacts={res.artifacts}"
    assert res.artifacts["passed"] is True

    # Check packet payload files_map: MUST NOT have tools/
    pkts = factory_repo.list_packets(job.id)
    verify_pkts = [p for p in pkts if p.node_id == "verify"]
    assert len(verify_pkts) > 0
    v_files = verify_pkts[-1].payload.get("files_map", {})
    assert "mcp/server.py" in v_files
    loose_tools = [k for k in v_files if k.startswith("tools/")]
    assert loose_tools == [], f"Verify injected loose tools: {loose_tools}"


@pytest.mark.asyncio
async def test_promote_factory_job_creates_mcp_pack_without_tools(factory_repo):
    with tempfile.TemporaryDirectory() as tmpdir:
        job = FactoryJob(
            id="job_promote_mcp_01",
            session_id="sess_test",
            target_agent_id="hyperv",
            seed_intent="Manage Hyper-V VMs and checkpoints",
            objectives=["Inspect VM status"],
            current_node_id="promote",
        )
        factory_repo.save_job(job)

        tool_specs = [{"name": "manage_hyperv_vm", "actions": ["status"], "description": "Hyper-V tool"}]
        files_map = {
            "mcp/server.py": _scaffold_mcp_server("hyperv", tool_specs, {}),
            "mcp/Dockerfile": "FROM python:3.11-slim",
            "skills/hyperv-vm-lifecycle/SKILL.md": (
                "---\nname: hyperv-vm-lifecycle\ndescription: desc\n---\n"
                "# Hyper-V\n## Purpose\ntest\n## Objectives\n- test\n"
                "## Prerequisites & Tools\nmanage_hyperv_vm\n"
                "## Standard Operating Procedure (SOP)\nstep 1\n"
                "## Available Actions\n- `status`: status\n## Error Handling\nnone\n"
            ),
        }
        pkt = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id="author",
            payload={
                "tool_name": "manage_hyperv_vm",
                "tool_names": ["manage_hyperv_vm"],
                "files_map": files_map,
            },
        )
        factory_repo.save_packet(pkt)

        class DummyState:
            pass

        class DummyDataPaths:
            root = Path(tmpdir)

        class DummyApp:
            state = DummyState()

        dummy_req = type("DummyRequest", (), {})()
        dummy_req.app = DummyApp()
        dummy_req.app.state.store = factory_repo._cm
        dummy_req.app.state.data_dir_paths = DummyDataPaths()
        dummy_req.app.state.registry = None
        dummy_req.app.state.mcp_client_manager = None
        dummy_req.app.state.tool_reg = None

        from src.web.routers.agent_training_factory import promote_factory_job

        res = await promote_factory_job(job.id, dummy_req)
        assert res["success"] is True
        pack_dir = Path(res["pack_dir"])
        assert pack_dir.is_dir()
        assert (pack_dir / "mcp" / "server.py").is_file()
        assert (pack_dir / "mcp" / "Dockerfile").is_file()
        assert (pack_dir / "skills" / "hyperv-vm-lifecycle" / "SKILL.md").is_file()
        assert not (pack_dir / "tools").exists()

        # Check pack.json
        pack_json = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
        assert "mcp_servers" in pack_json
        assert pack_json["mcp_servers"][0]["transport"] == "sse"
        assert pack_json["mcp_servers"][0]["url"] == "http://localhost:8080/sse"


