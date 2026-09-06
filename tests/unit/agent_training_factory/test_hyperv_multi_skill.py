"""CARD-171: Hyper-V multi-skill blueprint/author/promote (not one fat manage_hyperv)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.application.agent_training_factory.phases.blueprint import (
    BlueprintPhase,
    hyperv_lifecycle_blueprint,
)
from src.application.orchestration.capability_graph import ToolConsolidationGate, UserPackFinalizer
from src.application.orchestration.tool_synthesizer import ToolSynthesizer
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

HYPERV_MULTI_SEED = (
    "Hyper-V specialist covering Windows VM templates, unattended Autounattend ISO installs "
    "(OS ISO at D:\\Archive\\Tech\\Labs\\installers\\2022.ISO), routine template patching/"
    "maintenance, VM lifecycle (create/start/stop/checkpoint/remove), and virtual switch/"
    "networking lifecycle."
)
HYPERV_MULTI_OBJECTIVES = [
    "Windows VM templates: create reusable Generation-2 template VMs",
    "Unattended installs: build Autounattend.xml + answer ISO; mount OS ISO 2022.ISO",
    "Template maintenance: patch and maintain template VMs with checkpoints",
    "VM lifecycle: New-VM/Start-VM/Stop-VM/Checkpoint-VM/Remove-VM + status",
    "Networking: New-VMSwitch/Get-VMSwitch/Remove-VMSwitch and attach NICs",
]

EXPECTED_SKILL_IDS = {
    "hyperv-vm-lifecycle",
    "hyperv-networking",
    "hyperv-unattend-templates",
    "hyperv-template-maintenance",
}


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


def test_hyperv_lifecycle_blueprint_has_four_non_overlapping_skills():
    bp = hyperv_lifecycle_blueprint("hyperv", HYPERV_MULTI_SEED, HYPERV_MULTI_OBJECTIVES)
    skill_ids = {s["id"] for s in bp["skills"]}
    assert EXPECTED_SKILL_IDS.issubset(skill_ids)
    tool_names = [t["name"] for t in bp["tools"]]
    assert len(tool_names) == len(set(tool_names))
    assert "manage_hyperv" not in tool_names
    entities = {t.get("target_entity") for t in bp["tools"]}
    assert len(entities) >= 3


def test_consolidation_gate_preserves_distinct_lifecycle_entities():
    gate = ToolConsolidationGate()
    tools = [
        {"name": "manage_hyperv_vm", "target_entity": "hyperv_vm", "verb": "manage"},
        {"name": "manage_hyperv_network", "target_entity": "hyperv_network", "verb": "manage"},
        {"name": "manage_hyperv_unattend", "target_entity": "hyperv_unattend", "verb": "manage"},
    ]
    result = gate.evaluate(tools)
    assert result["should_consolidate"] is False


@pytest.mark.asyncio
async def test_blueprint_phase_keeps_multi_skill_for_hyperv_lifecycles(factory_repo):
    job = FactoryJob(
        id="fjob_bp_multi",
        target_agent_id="hyperv",
        session_id="sess_bp",
        status="running",
        seed_intent=HYPERV_MULTI_SEED,
        objectives=list(HYPERV_MULTI_OBJECTIVES),
        current_node_id="blueprint",
        environment_manifest_json=json.dumps(
            {
                "target_medium": "cli",
                "discovered_modules": ["Hyper-V"],
                "discovered_binaries": ["powershell.exe"],
            }
        ),
    )
    factory_repo.save_job(job)
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=MagicMock())
    result = await BlueprintPhase().run(ctx)
    assert result.outcome == "ok"
    bp = result.artifacts["blueprint"]
    skill_ids = {s["id"] for s in bp["skills"]}
    assert len(bp["skills"]) >= 3
    assert len(bp["tools"]) >= 3
    assert EXPECTED_SKILL_IDS.issubset(skill_ids) or len(skill_ids & EXPECTED_SKILL_IDS) >= 3
    # Must not collapse to single manage_hyperv
    tool_names = [t["name"] for t in bp["tools"]]
    assert not (len(tool_names) == 1 and tool_names[0] == "manage_hyperv")


@pytest.mark.asyncio
async def test_author_emits_all_blueprint_skills_and_tools(factory_repo):
    job = FactoryJob(
        id="fjob_author_multi",
        target_agent_id="hyperv",
        session_id="sess_a",
        status="running",
        seed_intent=HYPERV_MULTI_SEED,
        objectives=list(HYPERV_MULTI_OBJECTIVES),
        current_node_id="author",
        environment_manifest_json=json.dumps(
            {
                "target_medium": "cli",
                "discovered_modules": ["Hyper-V"],
                "discovered_binaries": ["powershell.exe"],
            }
        ),
    )
    factory_repo.save_job(job)
    bp = hyperv_lifecycle_blueprint("hyperv", HYPERV_MULTI_SEED, HYPERV_MULTI_OBJECTIVES)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id="blueprint",
            payload={"blueprint": bp, "proposed_tool": bp["tools"][0], "phase": "blueprint"},
        )
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    result = await AuthorPhase().run(ctx)
    assert result.outcome == "ok"
    files_map = result.artifacts["files_map"]
    skill_paths = [k for k in files_map if k.startswith("skills/") and k.endswith("SKILL.md")]
    tool_paths = [k for k in files_map if k.startswith("tools/") and k.endswith(".py")]
    assert len(skill_paths) >= 3
    assert len(tool_paths) >= 3
    joined_tools = "\n".join(files_map[k] for k in tool_paths)
    assert "Hyper-V\\New-VM" in joined_tools or "Hyper-V\\\\New-VM" in joined_tools
    assert "New-VMSwitch" in joined_tools or "Get-VMSwitch" in joined_tools
    assert "autounattend" in joined_tools.lower() or "Set-VMDvdDrive" in joined_tools
    # No Windows services bleed
    assert "Get-Service" not in joined_tools


def test_synthesizer_hyperv_focused_tools_include_domain_cmdlets():
    files = ToolSynthesizer.synthesize_tool(
        agent_id="hyperv",
        seed_intent=HYPERV_MULTI_SEED,
        objectives=HYPERV_MULTI_OBJECTIVES,
        tool_name="manage_hyperv_unattend",
        skill_id="hyperv-unattend-templates",
    )
    assert "skills/hyperv-unattend-templates/SKILL.md" in files
    tool_py = files["tools/manage_hyperv_unattend.py"]
    low = tool_py.lower()
    assert "autounattend" in low or "set-vmdvddrive" in low
    assert "2022.iso" in low or "iso_path" in low
    assert "get-service" not in low

    net = ToolSynthesizer.synthesize_tool(
        agent_id="hyperv",
        seed_intent="Hyper-V virtual switch and NIC lifecycle",
        objectives=["Create and remove VMSwitch", "Attach NIC to VM"],
        tool_name="manage_hyperv_network",
        skill_id="hyperv-networking",
    )
    net_py = net["tools/manage_hyperv_network.py"]
    assert "New-VMSwitch" in net_py or "Remove-VMSwitch" in net_py
    assert "Add-VMNetworkAdapter" in net_py or "connect_switch" in net_py.lower() or "attach" in net_py.lower()


def test_promote_merges_multi_skill_files_into_pack_manifest(tmp_path):
    """Promote path helpers must register each skills/<id>/SKILL.md as its own skill."""
    from src.web.routers.agent_training_factory import _skills_from_files_map

    files_map = {
        "tools/manage_hyperv_vm.py": "def manage_hyperv_vm():\n    pass\n",
        "tools/manage_hyperv_network.py": "def manage_hyperv_network():\n    pass\n",
        "skills/hyperv-vm-lifecycle/SKILL.md": "---\nname: VM Lifecycle\ntools:\n- manage_hyperv_vm\n---\n",
        "skills/hyperv-networking/SKILL.md": "---\nname: Networking\ntools:\n- manage_hyperv_network\n---\n",
    }
    skills = _skills_from_files_map(files_map)
    ids = {s["id"] for s in skills}
    assert "hyperv-vm-lifecycle" in ids
    assert "hyperv-networking" in ids
    tools = {t for s in skills for t in s.get("tools") or []}
    assert "manage_hyperv_vm" in tools
    assert "manage_hyperv_network" in tools

    finalizer = UserPackFinalizer(data_dir=str(tmp_path))
    pack_dir = finalizer.finalize_pack(
        agent_id="hyperv",
        manifest_data={
            "id": "hyperv",
            "name": "HyperV",
            "skills": skills,
            "pack_tool_names": ["manage_hyperv_vm", "manage_hyperv_network"],
            "allowed_skill": ["hyperv-vm-lifecycle", "hyperv-networking", "wiki"],
        },
        files=files_map,
    )
    pack = json.loads((Path(pack_dir) / "pack.json").read_text(encoding="utf-8"))
    assert len(pack["skills"]) >= 2
    assert (Path(pack_dir) / "skills/hyperv-vm-lifecycle/SKILL.md").is_file()
    assert (Path(pack_dir) / "skills/hyperv-networking/SKILL.md").is_file()
