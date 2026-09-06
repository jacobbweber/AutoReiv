"""Factory quality gates: no prose-theater scenario pass; brief-focused Hyper-V blueprints."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.blueprint import (
    hyperv_focus_from_brief,
    hyperv_lifecycle_blueprint,
)
from src.application.agent_training_factory.phases.scenario_verify import (
    ScenarioVerifyPhase,
    _scenario_covered,
    _tool_code_corpus,
)
from src.application.agent_training_factory.registry import PHASE_AUTHOR, PHASE_SCENARIO_VERIFY
from src.application.orchestration.hyperv_tool_builders import ACTIONS, build_hyperv_python_tool
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


def test_tool_code_corpus_ignores_skill_md_prose():
    files_map = {
        "skills/demo/SKILL.md": "Must call Hyper-V\\Restore-VMSnapshot and Hyper-V\\Remove-VMSnapshot",
        "tools/manage_demo.py": "def manage_demo(action='status'):\n    return {'ok': True}\n",
    }
    corpus = _tool_code_corpus(files_map)
    assert "restore-vmsnapshot" not in corpus
    assert "manage_demo" in corpus


def test_scenario_covered_fails_when_cmdlet_only_in_skill_prose():
    files_map = {
        "skills/hyperv-vm-lifecycle/SKILL.md": (
            "DONE-WHEN restore via Hyper-V\\Restore-VMSnapshot and remove via Hyper-V\\Remove-VMSnapshot"
        ),
        "tools/manage_hyperv_vm.py": (
            "def manage_hyperv_vm(action='checkpoint'):\n"
            "    ps = \"Hyper-V\\\\Checkpoint-VM -Name x\"\n"
            "    return ps\n"
        ),
        "tools/manage_hyperv_vm.ps1": (
            'switch ($Action) { "checkpoint" { Hyper-V\\Checkpoint-VM -Name $Name } }'
        ),
    }
    scen = "DONE-WHEN: Can apply/restore a checkpoint via Hyper-V\\Restore-VMSnapshot with confirmation"
    assert _scenario_covered(scen, files_map) is False


def test_scenario_covered_passes_when_cmdlet_in_tool_code():
    files_map = {
        "skills/hyperv-vm-lifecycle/SKILL.md": "Purpose only",
        "tools/manage_hyperv_vm.py": (
            "elif action == 'restore_checkpoint':\n"
            "    ps_cmd = \"Hyper-V\\\\Restore-VMSnapshot -Name 'snap' -VMName 'vm' -Confirm:$false\"\n"
        ),
        "tools/manage_hyperv_vm.ps1": (
            '"restore_checkpoint" { Hyper-V\\Restore-VMSnapshot -Name $SnapshotName -VMName $Name -Confirm:$false }'
        ),
    }
    scen = "DONE-WHEN: Can apply/restore a checkpoint via Hyper-V\\Restore-VMSnapshot with confirmation"
    assert _scenario_covered(scen, files_map) is True


@pytest.mark.asyncio
async def test_scenario_verify_fails_prose_theater(factory_repo):
    job = FactoryJob(
        id="fjob_theater",
        target_agent_id="hyperv",
        session_id="sess_t",
        status="running",
        seed_intent="checkpoint lifecycle",
        objectives=[
            "DONE-WHEN: restore via Hyper-V\\Restore-VMSnapshot",
            "DONE-WHEN: remove via Hyper-V\\Remove-VMSnapshot",
        ],
        current_node_id=PHASE_SCENARIO_VERIFY,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id="blueprint",
            payload={
                "blueprint": {
                    "skills": [{"id": "hyperv-vm-lifecycle", "tools": ["manage_hyperv_vm"]}],
                    "tools": [{"name": "manage_hyperv_vm", "actions": ["checkpoint"]}],
                    "scenarios": [
                        "DONE-WHEN: restore via Hyper-V\\Restore-VMSnapshot",
                        "DONE-WHEN: remove via Hyper-V\\Remove-VMSnapshot",
                    ],
                }
            },
        )
    )
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="scenario_verify",
            node_id=PHASE_AUTHOR,
            payload={
                "files_map": {
                    "skills/hyperv-vm-lifecycle/SKILL.md": (
                        "Purpose quotes Hyper-V\\Restore-VMSnapshot and Hyper-V\\Remove-VMSnapshot"
                    ),
                    "tools/manage_hyperv_vm.py": (
                        "def manage_hyperv_vm(action='checkpoint'):\n"
                        "    return 'Hyper-V\\\\Checkpoint-VM'\n"
                    ),
                    "tools/manage_hyperv_vm.ps1": (
                        '"checkpoint" { Hyper-V\\Checkpoint-VM -Name $Name }'
                    ),
                }
            },
        )
    )
    result = await ScenarioVerifyPhase().run(PhaseContext(job=job, repo=factory_repo))
    assert result.outcome != "ok"
    assert result.artifacts.get("passed") is False
    misses = result.artifacts.get("missing_scenarios") or []
    assert any("Restore-VMSnapshot" in m for m in misses)


def test_checkpoint_brief_focuses_vm_only_excludes_unattend():
    seed = (
        "manage Hyper-V VM checkpoints using Checkpoint-VM Get-VMSnapshot "
        "Restore-VMSnapshot Remove-VMSnapshot. No unattend, no oscdimg, no ISO download tooling."
    )
    objs = ["DONE-WHEN: create checkpoint", "DONE-WHEN: restore checkpoint"]
    focuses = hyperv_focus_from_brief("hyperv", seed, objs)
    assert focuses == {"vm"}
    bp = hyperv_lifecycle_blueprint("hyperv", seed, objs, focuses=focuses)
    skill_ids = {s["id"] for s in bp["skills"]}
    assert skill_ids == {"hyperv-vm-lifecycle"}
    assert "hyperv-unattend-templates" not in skill_ids
    vm_tool = next(t for t in bp["tools"] if t["name"] == "manage_hyperv_vm")
    for action in ("list_checkpoints", "restore_checkpoint", "remove_checkpoint", "checkpoint"):
        assert action in vm_tool["actions"]


def test_network_brief_focuses_network_only():
    seed = (
        "create/list/remove private or internal VM switches; attach/detach VM network adapters "
        "using New-VMSwitch Get-VMSwitch Remove-VMSwitch Add-VMNetworkAdapter Connect-VMNetworkAdapter. "
        "Native Hyper-V module only. No unattend."
    )
    focuses = hyperv_focus_from_brief("hyperv", seed, ["DONE-WHEN: create switch"])
    assert focuses == {"network"}
    bp = hyperv_lifecycle_blueprint("hyperv", seed, [], focuses=focuses)
    assert {s["id"] for s in bp["skills"]} == {"hyperv-networking"}


def test_vm_builder_emits_restore_and_remove_snapshot_cmdlets():
    assert "list_checkpoints" in ACTIONS["vm"]
    assert "restore_checkpoint" in ACTIONS["vm"]
    assert "remove_checkpoint" in ACTIONS["vm"]
    src = build_hyperv_python_tool(
        agent_id="hyperv",
        tool_name="manage_hyperv_vm",
        seed_intent="checkpoint lifecycle Restore-VMSnapshot Remove-VMSnapshot",
        objectives=["list", "restore", "remove checkpoints"],
        focus="vm",
    )
    assert "Restore-VMSnapshot" in src
    assert "Remove-VMSnapshot" in src
    assert "Get-VMSnapshot" in src
    assert "list_checkpoints" in src


def test_network_builder_excludes_unattend_and_checkpoint_bleed():
    src = build_hyperv_python_tool(
        agent_id="hyperv",
        tool_name="manage_hyperv_network",
        seed_intent="VM switches and NIC attach. No unattend, no oscdimg.",
        objectives=["DONE-WHEN: create switch", "DONE-WHEN: attach nic"],
        focus="network",
    )
    assert "New-VMSwitch" in src
    assert "Connect-VMNetworkAdapter" in src
    assert "build_autounattend" not in src
    assert "Checkpoint-VM" not in src
    assert "Get-Service" not in src


def test_vm_builder_excludes_unattend_and_switch_bleed():
    src = build_hyperv_python_tool(
        agent_id="hyperv",
        tool_name="manage_hyperv_vm",
        seed_intent="checkpoint Restore-VMSnapshot Remove-VMSnapshot. No unattend.",
        objectives=["DONE-WHEN: restore checkpoint"],
        focus="vm",
    )
    assert "Restore-VMSnapshot" in src
    assert "Remove-VMSnapshot" in src
    assert "list_checkpoints" in src
    assert "build_autounattend" not in src
    assert "New-VMSwitch" not in src


@pytest.mark.asyncio
async def test_scenario_verify_fails_forbidden_unattend_bleed(factory_repo):
    job = FactoryJob(
        id="fjob_bleed",
        target_agent_id="hyperv",
        session_id="sess_b",
        status="running",
        seed_intent="checkpoint lifecycle. No unattend, no oscdimg, no ISO download tooling.",
        objectives=["DONE-WHEN: restore via Hyper-V\\Restore-VMSnapshot"],
        current_node_id=PHASE_SCENARIO_VERIFY,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="gap",
            sender_role="blueprint",
            recipient_role="author",
            node_id="blueprint",
            payload={
                "blueprint": {
                    "skills": [{"id": "hyperv-vm-lifecycle", "tools": ["manage_hyperv_vm"]}],
                    "tools": [{"name": "manage_hyperv_vm", "actions": ["restore_checkpoint"]}],
                    "scenarios": ["DONE-WHEN: restore via Hyper-V\\Restore-VMSnapshot"],
                }
            },
        )
    )
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="scenario_verify",
            node_id=PHASE_AUTHOR,
            payload={
                "files_map": {
                    "skills/hyperv-vm-lifecycle/SKILL.md": "Purpose checkpoint",
                    "tools/manage_hyperv_vm.py": (
                        "elif action == 'restore_checkpoint':\n"
                        "    ps = \"Hyper-V\\\\Restore-VMSnapshot\"\n"
                        "elif action == 'build_autounattend':\n"
                        "    ps = 'imapi2fs'\n"
                    ),
                    "tools/manage_hyperv_vm.ps1": (
                        '"restore_checkpoint" { Hyper-V\\Restore-VMSnapshot -Name $SnapshotName -VMName $Name }'
                    ),
                }
            },
        )
    )
    result = await ScenarioVerifyPhase().run(PhaseContext(job=job, repo=factory_repo))
    assert result.artifacts.get("passed") is False
    misses = result.artifacts.get("missing_scenarios") or []
    assert any("FORBIDDEN_BLEED" in m for m in misses)
