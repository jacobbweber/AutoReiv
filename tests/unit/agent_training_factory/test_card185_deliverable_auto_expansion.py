"""Unit tests for CARD-185: Deliverable Auto-Detection, Existing Pack Expansion, and Skill Runbook Content Alignment."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.application.agent_training_factory.phases.blueprint import (
    classify_deliverable_type,
)
from src.application.agent_training_factory.phases.verify import VerifyPhase
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def factory_repo(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    store.initialize_db()
    return FactoryPacketRepository(store)


def test_classify_deliverable_type_skill_explicit():
    """AC-1: Explicitly requested 'skill' deliverable type must return 'skill'."""
    assert classify_deliverable_type("hyperv", "Manage Hyper-V", requested_type="skill") == "skill"
    assert classify_deliverable_type("writer", "Write documentation", requested_type="skill") == "skill"


def test_classify_deliverable_type_auto_detects_existing_mcp_pack(tmp_path):
    """AC-2: When requested_type is 'auto', existing agent pack with MCP server must classify as 'mcp'."""
    agent_dir = tmp_path / "packs" / "custom-agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "custom-agent",
        "name": "Custom Agent",
        "mcp_servers": [
            {"name": "custom_srv", "transport": "sse", "url": "http://localhost:9000/sse"}
        ],
    }
    (agent_dir / "pack.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = classify_deliverable_type(
        "custom-agent",
        "Generic task description",
        requested_type="auto",
        data_dir=tmp_path,
    )
    assert result == "mcp"


@pytest.mark.asyncio
async def test_author_phase_distinct_skill_titles_and_clean_objectives(factory_repo):
    """AC-3, AC-4: Multi-skill run must not bleed first skill's title or dump raw prompt text into objectives."""
    job = FactoryJob(
        id="fjob_titles_bleed_test",
        target_agent_id="hyperv",
        session_id="sess_bleed",
        status="running",
        seed_intent=(
            "We need to train on Managing all aspects of Hyper-V via the use of skills and MCP. "
            "We need capabilities that extend beyond just managing the VM, we should account for networking."
        ),
        objectives=[
            "We need to train on Managing all aspects of Hyper-V via the use of skills and MCP. "
            "We need capabilities that extend beyond just managing the VM, we should account for networking."
        ],
        current_node_id="author",
    )
    factory_repo.save_job(job)

    blueprint = {
        "deliverable_type": "mcp",
        "skills": [
            {
                "id": "hyperv-vm-lifecycle",
                "name": "Hyper-V VM Lifecycle",
                "description": "Create, start, stop, checkpoint, and remove VMs.",
                "tools": ["manage_hyperv_vm"],
            },
            {
                "id": "hyperv-networking",
                "name": "Hyper-V Networking",
                "description": "Virtual switch lifecycle and NIC attachment.",
                "tools": ["manage_hyperv_network"],
            },
        ],
        "tools": [
            {
                "name": "manage_hyperv_vm",
                "skill_id": "hyperv-vm-lifecycle",
                "actions": ["status", "start", "stop", "checkpoint"],
            },
            {
                "name": "manage_hyperv_network",
                "skill_id": "hyperv-networking",
                "actions": ["list_switches", "create_switch", "attach_nic"],
            },
        ],
    }
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id="blueprint",
            payload={"blueprint": blueprint, "proposed_tool": blueprint["tools"][0], "phase": "blueprint"},
        )
    )

    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    result = await AuthorPhase().run(ctx)
    assert result.outcome == "ok"
    files = result.artifacts["files_map"]

    # Check hyperv-vm-lifecycle
    vm_skill = files.get("skills/hyperv-vm-lifecycle/SKILL.md", "")
    assert "# Hyper-V VM Lifecycle" in vm_skill

    # Check hyperv-networking: MUST NOT have "# Hyper-V VM Lifecycle" title!
    net_skill = files.get("skills/hyperv-networking/SKILL.md", "")
    assert "# Hyper-V Networking" in net_skill
    assert "# Hyper-V VM Lifecycle" not in net_skill

    # Neither skill should contain raw user instruction prompt dumped into Objectives
    assert "We need to train on" not in net_skill
    assert "We need to train on" not in vm_skill


@pytest.mark.asyncio
async def test_author_phase_skill_only_deliverable(factory_repo):
    """AC-1: Skill-only deliverable authors runbooks and zero tools or MCP files."""
    job = FactoryJob(
        id="fjob_skill_only_test",
        target_agent_id="doc-reviewer",
        session_id="sess_skill_only",
        status="running",
        seed_intent="Review architecture documentation for completeness and clarity",
        objectives=["Review RFC documents", "Check diagrams against specs"],
        current_node_id="author",
    )
    factory_repo.save_job(job)

    blueprint = {
        "deliverable_type": "skill",
        "skills": [
            {
                "id": "review-rfc",
                "name": "Review RFCs",
                "description": "Review RFC documents according to engineering standards.",
                "tools": [],
            },
            {
                "id": "diagram-audit",
                "name": "Diagram Audit",
                "description": "Audit system architecture diagrams.",
                "tools": [],
            },
        ],
        "tools": [],
    }
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id="blueprint",
            payload={"blueprint": blueprint, "proposed_tool": {}, "phase": "blueprint"},
        )
    )

    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    result = await AuthorPhase().run(ctx)
    assert result.outcome == "ok"
    files = result.artifacts["files_map"]

    # Verify skills are authored
    assert "skills/review-rfc/SKILL.md" in files
    assert "skills/diagram-audit/SKILL.md" in files

    # Verify ZERO tools and ZERO MCP files
    tool_files = [k for k in files if k.startswith("tools/") or k.startswith("mcp/")]
    assert len(tool_files) == 0


@pytest.mark.asyncio
async def test_verify_phase_reports_all_tools(factory_repo):
    """AC-5: Verify battery summary must mention all verified tools, not just the first one."""
    job = FactoryJob(
        id="fjob_verify_all_tools",
        target_agent_id="hyperv",
        session_id="sess_verify",
        status="running",
        seed_intent="Hyper-V lifecycle and networking",
        objectives=["VM management", "Network management"],
        current_node_id="verify",
    )
    factory_repo.save_job(job)

    mock_battery = MagicMock()
    eval_pkt = MagicMock()
    eval_pkt.passed = True
    eval_pkt.stage_1_functional = True
    eval_pkt.stage_2_safety = True
    eval_pkt.stage_3_idempotency = True
    eval_pkt.stage_4_critic = True
    eval_pkt.critic_notes = ""
    eval_pkt.duration_ms = 120.0
    eval_pkt.stdout = ""
    eval_pkt.stderr = ""
    mock_battery.run_battery = AsyncMock(return_value=eval_pkt)
    mock_battery.run_mcp_battery = AsyncMock(return_value=eval_pkt)

    tools = ["manage_hyperv_vm", "manage_hyperv_network", "manage_hyperv_unattend"]
    files_map = {
        f"tools/{t}.py": f"def {t}(): return {{'success': True}}" for t in tools
    }
    files_map["skills/hyperv-vm-lifecycle/SKILL.md"] = "---\nname: hyperv-vm-lifecycle\ndescription: runbook\n---\n## Purpose\nVM\n## Objectives\n- VM\n"

    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id="author",
            payload={
                "tool_names": tools,
                "tool_name": tools[0],
                "files_map": files_map,
                "phase": "author",
            },
        )
    )

    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, battery=mock_battery)
    result = await VerifyPhase().run(ctx)
    assert result.outcome == "ok"
    for t in tools:
        assert t in result.message
