"""
Unit tests for Deliverables Taxonomy: MCP Servers, Native Tools, and Skill Runbooks [CARD-176].
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.application.agent_training_factory.phases.blueprint import (
    BlueprintPhase,
    classify_deliverable_type,
)
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for s in ("", "-wal", "-shm"):
        p = path + s
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


def test_classify_deliverable_type():
    # 1. Explicit request wins
    assert classify_deliverable_type("finance", "manage budget", requested_type="mcp") == "mcp"
    assert classify_deliverable_type("hyperv", "manage vms", requested_type="native_tool") == "native_tool"

    # 2. System/Infrastructure domain auto-classifies to MCP
    assert classify_deliverable_type("hyperv", "Hyper-V virtual machine lifecycle", requested_type="auto") == "mcp"
    assert classify_deliverable_type("docker-agent", "Docker container manager", requested_type="auto") == "mcp"
    assert classify_deliverable_type("sysadmin", "PowerShell Windows service manager", requested_type="auto") == "mcp"

    # 3. Local data / calculation auto-classifies to native_tool
    assert classify_deliverable_type("personal-finance", "Personal budget tracker with SQLite", requested_type="auto") == "native_tool"
    assert classify_deliverable_type("text-helper", "Format markdown summaries", requested_type="auto") == "native_tool"


@pytest.mark.asyncio
async def test_blueprint_phase_emits_deliverable_type(temp_db):
    store = SQLiteStateStore(temp_db)
    store.initialize_db()
    repo = FactoryPacketRepository(store)

    job = FactoryJob(
        id="fjob_blueprint_mcp",
        target_agent_id="hyperv-specialist",
        session_id="sess_1",
        seed_intent="Manage Hyper-V VM checkpoints and snapshots",
        objectives=["List checkpoints", "Create checkpoint"],
    )
    repo.save_job(job)

    # Add initial work packet with deliverable_type = "auto"
    repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="orchestrator",
            recipient_role="blueprint",
            node_id="intent_distill",
            payload={"deliverable_type": "auto"},
        )
    )

    ctx = PhaseContext(job=job, repo=repo)
    phase = BlueprintPhase()
    res = await phase.run(ctx)

    assert res.outcome == "ok"
    blueprint = res.artifacts.get("blueprint", {})
    assert blueprint.get("deliverable_type") == "mcp"
    tools = blueprint.get("tools", [])
    assert len(tools) > 0
    assert all(t.get("deliverable_type") == "mcp" for t in tools)


@pytest.mark.asyncio
async def test_author_phase_scaffolds_mcp_server_and_structured_skill(temp_db):
    store = SQLiteStateStore(temp_db)
    store.initialize_db()
    repo = FactoryPacketRepository(store)

    job = FactoryJob(
        id="fjob_author_mcp",
        target_agent_id="hyperv-manager",
        session_id="sess_2",
        seed_intent="Manage Hyper-V VM checkpoints via PowerShell",
        objectives=["Checkpoint VMs", "List VM snapshots"],
    )
    repo.save_job(job)

    # Save blueprint packet declaring mcp deliverable
    repo.save_packet(
        FactoryPacket(
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
                            "description": "Create and restore checkpoints",
                            "tools": ["manage_hyperv_vm"],
                        }
                    ],
                    "tools": [
                        {
                            "name": "manage_hyperv_vm",
                            "deliverable_type": "mcp",
                            "actions": ["status", "checkpoint", "list_checkpoints"],
                            "description": "Hyper-V checkpoint dispatcher",
                            "skill_id": "hyperv-vm-lifecycle",
                        }
                    ],
                }
            },
        )
    )

    ctx = PhaseContext(job=job, repo=repo)
    phase = AuthorPhase()
    res = await phase.run(ctx)

    assert res.outcome == "ok"
    files_map = res.artifacts.get("files_map", {})
    # 1. MCP Server scaffolded
    assert "mcp/server.py" in files_map
    server_code = files_map["mcp/server.py"]
    assert "PackMCPServer" in server_code
    assert "manage_hyperv_vm" in server_code

    # 2. SKILL.md formatted with trigger YAML frontmatter and structured SOP
    skill_file = "skills/hyperv-vm-lifecycle/SKILL.md"
    assert skill_file in files_map
    skill_md = files_map[skill_file]
    assert skill_md.strip().startswith("---")
    assert "description:" in skill_md
    assert "## Purpose & Scope" in skill_md
    assert "## Standard Operating Procedure (SOP)" in skill_md
    assert "## Error Handling & Recovery" in skill_md


@pytest.mark.asyncio
async def test_verification_battery_mcp_server():
    from src.application.orchestration.verification_battery import VerificationBatteryService

    battery = VerificationBatteryService()
    server_code = """
from src.infrastructure.mcp.pack_server import PackMCPServer

server = PackMCPServer(name="test_battery_server")

@server.tool(name="manage_test", description="Test dispatcher")
def manage_test(action: str = "status", **kwargs) -> dict:
    return {"success": True, "action": action, "output": f"Handled {action}"}

if __name__ == "__main__":
    server.run_stdio()
"""
    tool_code = """
def manage_test(action="status", **kwargs):
    return {"success": True, "action": action}
"""
    skill_content = """---
name: test-skill
description: Use when running test operations.
---

# Test Runbook

## 1. Purpose & Scope
Testing automation.

### Key Objectives
- Run status action

## 2. Prerequisites & Environment
None.

## 3. Standard Operating Procedure (SOP)
Run status action.

## 4. Input & Parameter Reference
action: status

## 5. Error Handling & Recovery
Retry on error.
"""
    packet = await battery.run_mcp_battery(
        server_code=server_code,
        expected_tools=["manage_test"],
        tool_code=tool_code,
        skill_content=skill_content,
        seed_intent="Testing automation with MCP",
        objectives=["Run status action"],
        repeats=2,
    )

    assert packet.passed is True
    assert packet.stage_1_functional is True
    assert packet.stage_2_safety is True
    assert packet.stage_3_idempotency is True
    assert packet.stage_4_critic is True
    assert "MCP Server verified" in packet.critic_notes


@pytest.mark.asyncio
async def test_verification_battery_mcp_ast_critic_rejection():
    from src.application.orchestration.verification_battery import VerificationBatteryService

    battery = VerificationBatteryService()
    server_code_with_eval = """
from src.infrastructure.mcp.pack_server import PackMCPServer

server = PackMCPServer(name="insecure_server")

@server.tool(name="dangerous", description="Insecure eval")
def dangerous(code: str) -> dict:
    return {"res": eval(code)}

if __name__ == "__main__":
    server.run_stdio()
"""
    packet = await battery.run_mcp_battery(
        server_code=server_code_with_eval,
        expected_tools=["dangerous"],
    )

    assert packet.passed is False
    assert packet.stage_4_critic is False
    assert "eval" in packet.critic_notes


@pytest.mark.asyncio
async def test_verify_phase_with_mcp_server(temp_db):
    from src.application.agent_training_factory.phases.verify import VerifyPhase

    store = SQLiteStateStore(temp_db)
    store.initialize_db()
    repo = FactoryPacketRepository(store)

    job = FactoryJob(
        id="fjob_verify_mcp",
        target_agent_id="test-agent",
        session_id="sess_3",
        seed_intent="Test agent verification with MCP",
        objectives=["Test action status"],
    )
    repo.save_job(job)

    server_code = """
from src.infrastructure.mcp.pack_server import PackMCPServer

server = PackMCPServer(name="test_agent_server")

@server.tool(name="manage_test_agent", description="Test agent tool")
def manage_test_agent(action: str = "status", **kwargs) -> dict:
    return {"success": True, "action": action, "output": "ok"}

if __name__ == "__main__":
    server.run_stdio()
"""
    tool_code = """
def manage_test_agent(action="status", **kwargs):
    return {"success": True, "action": action}
"""
    skill_content = """---
name: test-agent-skill
description: Use when running test agent actions.
---

# Test Agent Runbook

## 1. Purpose & Scope
Test agent verification with MCP.

### Key Objectives
- Test action status

## 2. Prerequisites & Environment
None.

## 3. Standard Operating Procedure (SOP)
Execute action status.

## 4. Input & Parameter Reference
action: status

## 5. Error Handling & Recovery
Retry.
"""
    # Emulate author packet
    repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id="author",
            payload={
                "tool_name": "manage_test_agent",
                "tool_names": ["manage_test_agent"],
                "files_map": {
                    "mcp/server.py": server_code,
                    "tools/manage_test_agent.py": tool_code,
                    "skills/test-agent/SKILL.md": skill_content,
                },
            },
        )
    )

    ctx = PhaseContext(job=job, repo=repo)
    phase = VerifyPhase()
    res = await phase.run(ctx)

    assert res.outcome == "ok"
    assert "MCP Server deliverable" in res.message
    eval_runs = repo.list_eval_runs(job.id)
    assert len(eval_runs) == 1
    assert eval_runs[0].tool_name == "manage_test_agent_mcp"
    assert eval_runs[0].overall_passed is True


@pytest.mark.asyncio
async def test_promote_factory_job_persists_mcp_server_manifest(temp_db, tmp_path):
    from src.web.routers.agent_training_factory import promote_factory_job

    store = SQLiteStateStore(temp_db)
    store.initialize_db()
    repo = FactoryPacketRepository(store)

    job = FactoryJob(
        id="fjob_promote_mcp",
        target_agent_id="vault-agent",
        session_id="sess_promote",
        seed_intent="Secure secrets operator with MCP",
        objectives=["Read secret"],
    )
    repo.save_job(job)

    server_code = """
from src.infrastructure.mcp.pack_server import PackMCPServer

server = PackMCPServer(name="vault_server")

@server.tool(name="manage_vault", description="Vault tool")
def manage_vault(action: str = "status", **kwargs) -> dict:
    return {"success": True}

if __name__ == "__main__":
    server.run_stdio()
"""
    repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id="author",
            payload={
                "tool_name": "manage_vault",
                "tool_names": ["manage_vault"],
                "files_map": {
                    "mcp/server.py": server_code,
                    "tools/manage_vault.py": "def manage_vault(): pass\n",
                    "skills/vault/SKILL.md": "---\nname: vault\ndescription: vault\n---\n\n## Purpose\nVault\n",
                },
            },
        )
    )

    request = MagicMock()
    request.app.state.store = store
    request.app.state.factory_repo = repo
    paths_mock = MagicMock()
    paths_mock.root = str(tmp_path)
    request.app.state.data_dir_paths = paths_mock
    request.app.state.tool_reg = None
    request.app.state.tool_registry = None
    request.app.state.registry = None
    request.app.state.mcp_client_manager = None

    res = await promote_factory_job(job_id=job.id, request=request)
    assert res.get("success") is True

    pack_json_file = tmp_path / "packs" / "vault-agent" / "pack.json"
    assert pack_json_file.is_file()
    pack_data = json.loads(pack_json_file.read_text(encoding="utf-8"))
    assert "mcp_server" in pack_data
    assert pack_data["mcp_server"]["enabled"] is True
    assert pack_data["mcp_server"]["entrypoint"] == "mcp/server.py"

    server_py_file = tmp_path / "packs" / "vault-agent" / "mcp" / "server.py"
    assert server_py_file.is_file()
    assert "vault_server" in server_py_file.read_text(encoding="utf-8")

