"""Factory quality gates: no prose-theater scenario pass; brief-focused Hyper-V blueprints."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.application.agent_training_factory.phases.blueprint import (
    hyperv_focus_from_brief,
    hyperv_lifecycle_blueprint,
)
from src.application.agent_training_factory.phases.ground import (
    _build_operating_manual,
    _manual_has_structured_sop,
)
from src.application.agent_training_factory.phases.intent_distill import (
    _heuristic_answers,
    _sop_is_structured,
)
from src.application.agent_training_factory.phases.scenario_verify import (
    ScenarioVerifyPhase,
    _forbidden_bleed,
    _scenario_covered,
    _tool_code_corpus,
)
from src.application.agent_training_factory.question_battery import DEFAULT_INTENT_QUESTIONS
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
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=None)
    result = await ScenarioVerifyPhase().run(ctx)
    assert result.outcome != "ok"
    assert result.artifacts.get("passed") is False


def test_checkpoint_brief_focuses_checkpoint_only_excludes_unattend():
    seed = (
        "manage Hyper-V VM checkpoints using Checkpoint-VM Get-VMSnapshot "
        "Restore-VMSnapshot Remove-VMSnapshot only"
    )
    objs = ["DONE-WHEN: create checkpoint", "DONE-WHEN: restore checkpoint"]
    focuses = hyperv_focus_from_brief("hyperv", seed, objs)
    assert focuses == {"checkpoint"}
    bp = hyperv_lifecycle_blueprint("hyperv", seed, objs, focuses=focuses)
    assert len(bp["skills"]) == 1
    assert bp["skills"][0]["id"] == "hyperv-vm-lifecycle"
    assert len(bp["tools"]) == 1
    actions = set(bp["tools"][0].get("actions") or [])
    for action in ("list_checkpoints", "restore_checkpoint", "remove_checkpoint", "checkpoint"):
        assert action in actions
    assert "create" not in actions
    assert "create_switch" not in actions
    assert "build_autounattend" not in actions


def test_network_brief_focuses_network_only():
    seed = "Hyper-V virtual switch and NIC lifecycle New-VMSwitch Connect-VMNetworkAdapter"
    focuses = hyperv_focus_from_brief("hyperv", seed, ["DONE-WHEN: create switch"])
    assert focuses == {"network"}
    bp = hyperv_lifecycle_blueprint("hyperv", seed, [], focuses=focuses)
    assert {s["id"] for s in bp["skills"]} == {"hyperv-networking"}


def test_vm_builder_emits_restore_and_remove_snapshot_cmdlets():
    assert "list_checkpoints" in ACTIONS["checkpoint"]
    assert "restore_checkpoint" in ACTIONS["checkpoint"]
    assert "remove_checkpoint" in ACTIONS["checkpoint"]
    src = build_hyperv_python_tool(
        agent_id="hyperv",
        tool_name="manage_hyperv_vm",
        seed_intent="checkpoint lifecycle Restore-VMSnapshot Remove-VMSnapshot",
        objectives=["list", "restore", "remove checkpoints"],
        focus="checkpoint",
    )
    assert "Restore-VMSnapshot" in src
    assert "Remove-VMSnapshot" in src
    assert "list_checkpoints" in src
    assert "build_autounattend" not in src
    assert 'action == "create"' not in src and "action == 'create'" not in src


def test_network_builder_excludes_unattend_and_checkpoint_bleed():
    src = build_hyperv_python_tool(
        agent_id="hyperv",
        tool_name="manage_hyperv_network",
        seed_intent="switch NIC",
        objectives=["create switch"],
        focus="network",
    )
    assert "New-VMSwitch" in src
    assert "Checkpoint-VM" not in src
    assert "build_autounattend" not in src


def test_vm_builder_excludes_unattend_and_switch_bleed():
    src = build_hyperv_python_tool(
        agent_id="hyperv",
        tool_name="manage_hyperv_vm",
        seed_intent="checkpoint Restore-VMSnapshot Remove-VMSnapshot. No unattend.",
        objectives=["DONE-WHEN: restore checkpoint"],
        focus="checkpoint",
    )
    assert "Restore-VMSnapshot" in src
    assert "list_checkpoints" in src
    assert "New-VMSwitch" not in src
    assert "build_autounattend" not in src


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
                    "focuses": ["checkpoint"],
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
                        "FOCUS = \"checkpoint\"\n"
                        "elif action == 'restore_checkpoint':\n"
                        "    ps_cmd = \"Hyper-V\\\\Restore-VMSnapshot -Name 's' -VMName 'v'\"\n"
                        "elif action == 'build_autounattend':\n"
                        "    ps_cmd = 'oscdimg -build'\n"
                    ),
                    "tools/manage_hyperv_vm.ps1": (
                        '"restore_checkpoint" { Hyper-V\\Restore-VMSnapshot -Name $SnapshotName -VMName $Name }'
                    ),
                }
            },
        )
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=None)
    result = await ScenarioVerifyPhase().run(ctx)
    misses = result.artifacts.get("missing_scenarios") or []
    assert any("FORBIDDEN_BLEED" in m for m in misses)


def test_forbidden_bleed_uses_focus_without_explicit_no_unattend_phrase():
    """Network-focused brief must fail when tool still has unattend action branch."""
    files_map = {
        "tools/manage_hyperv_network.py": (
            'FOCUS = "network"\n'
            'elif action == "create_switch":\n'
            '    ps_cmd = "Hyper-V\\\\New-VMSwitch -Name x -SwitchType Internal"\n'
            'elif action == "build_autounattend":\n'
            '    ps_cmd = "write xml"\n'
        )
    }
    hits = _forbidden_bleed(
        files_map,
        seed_intent="NIC switch lifecycle New-VMSwitch Connect-VMNetworkAdapter",
        objectives=["DONE-WHEN: create switch via New-VMSwitch"],
        agent_id="hyperv",
    )
    assert hits, "expected focus-based forbidden bleed hits"
    assert any("build_autounattend" in h for h in hits)


def test_forbidden_bleed_ignores_negative_constraint_phrases_in_objectives():
    """'no oscdimg' inside OBJECTIVES / seed echo must not count as bleed."""
    files_map = {
        "tools/manage_hyperv_network.py": (
            'FOCUS = "network"\n'
            'OBJECTIVES: list = ["NIC switch. No unattend, no oscdimg."]\n'
            'elif action == "create_switch":\n'
            '    ps_cmd = "Hyper-V\\\\New-VMSwitch -Name x -SwitchType Internal"\n'
            'elif action == "attach_nic":\n'
            '    ps_cmd = "Hyper-V\\\\Connect-VMNetworkAdapter -VMName v -SwitchName x"\n'
        )
    }
    hits = _forbidden_bleed(
        files_map,
        seed_intent="NIC switch lifecycle New-VMSwitch Connect-VMNetworkAdapter. No unattend, no oscdimg.",
        objectives=["DONE-WHEN: create switch"],
        agent_id="hyperv",
    )
    assert hits == []


@pytest.mark.asyncio
async def test_author_rescopes_wide_blueprint_to_checkpoint_focus(factory_repo):
    job = FactoryJob(
        id="fjob_author_narrow",
        target_agent_id="hyperv",
        session_id="sess_an",
        status="running",
        seed_intent=(
            "checkpoint lifecycle Checkpoint-VM Get-VMSnapshot Restore-VMSnapshot Remove-VMSnapshot. "
            "No unattend, no ISO download."
        ),
        objectives=["DONE-WHEN: restore checkpoint via Restore-VMSnapshot"],
        current_node_id=PHASE_AUTHOR,
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
                    "skills": [
                        {"id": "hyperv-vm-lifecycle", "tools": ["manage_hyperv_vm"]},
                        {"id": "hyperv-networking", "tools": ["manage_hyperv_network"]},
                        {"id": "hyperv-unattend-templates", "tools": ["manage_hyperv_unattend"]},
                        {"id": "hyperv-template-maintenance", "tools": ["manage_hyperv_template"]},
                    ],
                    "tools": [
                        {"name": "manage_hyperv_vm", "actions": ["checkpoint"], "skill_id": "hyperv-vm-lifecycle"},
                        {"name": "manage_hyperv_network", "actions": ["create_switch"], "skill_id": "hyperv-networking"},
                        {"name": "manage_hyperv_unattend", "actions": ["build_autounattend"], "skill_id": "hyperv-unattend-templates"},
                        {"name": "manage_hyperv_template", "actions": ["list_templates"], "skill_id": "hyperv-template-maintenance"},
                    ],
                    "scenarios": ["DONE-WHEN: restore checkpoint via Restore-VMSnapshot"],
                }
            },
        )
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=None)
    result = await AuthorPhase().run(ctx)
    files = result.artifacts.get("files_map") or {}
    keys = set(files.keys())
    assert "tools/manage_hyperv_vm.py" in keys
    assert "tools/manage_hyperv_unattend.py" not in keys
    assert "tools/manage_hyperv_network.py" not in keys
    py = files["tools/manage_hyperv_vm.py"]
    assert "Restore-VMSnapshot" in py
    assert "build_autounattend" not in py
    assert "New-VMSwitch" not in py


def test_sop_rubric_rejects_brief_echo_and_accepts_structured():
    seed = "checkpoint lifecycle Checkpoint-VM only"
    echo = f"A professional SOP for this role covers: purpose... Brief: {seed}"
    assert _sop_is_structured(echo) is False
    structured = (
        "## Purpose\nManage VM checkpoints.\n"
        "## Steps\n1. Checkpoint-VM\n2. Get-VMSnapshot\n"
        "## Verify\nConfirm snapshot listed.\n"
        "## Rollback\nRemove-VMSnapshot if wrong.\n"
    )
    assert _sop_is_structured(structured) is True
    answers = _heuristic_answers(
        type("J", (), {"seed_intent": seed})(),
        list(DEFAULT_INTENT_QUESTIONS),
        ["DONE-WHEN: restore checkpoint"],
    )
    assert _sop_is_structured(answers["professional_sop"]) is True


def test_ground_manual_includes_structured_sop_sections():
    job = type("J", (), {"target_agent_id": "hyperv", "seed_intent": "switch lifecycle"})()
    manual = _build_operating_manual(
        job,
        "cli",
        ["DONE-WHEN: New-VMSwitch"],
        {"discovered_binaries": ["powershell.exe"], "discovered_modules": ["Hyper-V"]},
    )
    assert _manual_has_structured_sop(manual) is True
    assert "## Steps" in manual or "## Procedure" in manual
    assert "## Verify" in manual
    assert "## Rollback" in manual

def test_negated_switch_does_not_add_network_focus():
    seed = (
        "Hyper-V checkpoint lifecycle Checkpoint-VM Get-VMSnapshot Restore-VMSnapshot "
        "Remove-VMSnapshot. No New-VM, no switch/NIC, no unattend."
    )
    focuses = hyperv_focus_from_brief("hyperv", seed, ["DONE-WHEN: restore checkpoint"])
    assert focuses == {"checkpoint"}


@pytest.mark.asyncio
async def test_scenario_verify_flags_out_of_scope_network_tool_on_checkpoint_brief(factory_repo):
    job = FactoryJob(
        id="fjob_scope",
        target_agent_id="hyperv",
        session_id="sess_s",
        status="running",
        seed_intent="checkpoint only Checkpoint-VM Restore-VMSnapshot. No switch/NIC, no unattend.",
        objectives=["DONE-WHEN: restore via Hyper-V\\Restore-VMSnapshot"],
        current_node_id=PHASE_SCENARIO_VERIFY,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="scenario_verify",
            node_id=PHASE_AUTHOR,
            payload={
                "files_map": {
                    "tools/manage_hyperv_vm.py": (
                        "FOCUS = \"checkpoint\"\n"
                        "elif action == \"restore_checkpoint\":\n"
                        "    ps_cmd = \"Hyper-V\\\\Restore-VMSnapshot\"\n"
                    ),
                    "tools/manage_hyperv_network.py": (
                        "FOCUS = \"network\"\n"
                        "elif action == \"create_switch\":\n"
                        "    ps_cmd = \"Hyper-V\\\\New-VMSwitch\"\n"
                    ),
                }
            },
        )
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=None)
    result = await ScenarioVerifyPhase().run(ctx)
    misses = result.artifacts.get("missing_scenarios") or []
    assert any("OUT_OF_SCOPE_FILES" in m for m in misses)
