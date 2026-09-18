"""Unit tests for GroundPhase real directory inspection [REQ-FACT-065]."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.ground import GroundPhase
from src.domain.orchestration.factory_packets import FactoryJob, WorkPacket


@pytest.mark.asyncio
async def test_ground_phase_inspects_real_target_directory(tmp_path):
    # Set up mock target project directory
    proj_dir = tmp_path / "homelab_project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    tofu_dir = proj_dir / "tofu"
    tofu_dir.mkdir(parents=True, exist_ok=True)
    (tofu_dir / "main.tf").write_text('resource "hyperv_vm" "vm1" {}', encoding="utf-8")

    ansible_dir = proj_dir / "ansible"
    ansible_dir.mkdir(parents=True, exist_ok=True)
    (ansible_dir / "site.yml").write_text("- hosts: all\n  tasks: []", encoding="utf-8")

    ps_dir = proj_dir / "scripts"
    ps_dir.mkdir(parents=True, exist_ok=True)
    (ps_dir / "deploy.ps1").write_text("Write-Host 'Deploying'", encoding="utf-8")

    # Set up job and repo
    job = FactoryJob(
        id="fjob_test123",
        target_agent_id="homelab-admin",
        session_id="sess_test",
        seed_intent="Learn tooling in our directory to spin up homelab with opentofu and ansible",
        objectives=["Deploy VM"],
    )

    work_pkt = WorkPacket(
        goal=job.seed_intent,
        target_agent_id=job.target_agent_id,
        facts=job.objectives,
        done_when="Test done",
        target_directory=str(proj_dir),
    )

    repo = MagicMock()
    repo.list_packets.return_value = [
        MagicMock(sender_role="orchestrator", payload=work_pkt.model_dump())
    ]

    gateway = MagicMock()
    gateway.default_model_id = "test-model"
    gateway.complete = AsyncMock()

    ctx = PhaseContext(
        job=job,
        repo=repo,
        gateway=gateway,
        wiki=None,
        store=None,
    )

    phase = GroundPhase()
    result = await phase.run(ctx)

    assert result.outcome in ("ok", "skip_blueprint")
    manifest = result.artifacts.get("manifest", {})
    files_tree = manifest.get("files_tree", [])
    rel_paths = [f.get("relative_path") for f in files_tree]

    assert any("main.tf" in p for p in rel_paths)
    assert any("site.yml" in p for p in rel_paths)
    assert any("deploy.ps1" in p for p in rel_paths)

    # Verify operating manual mentions the files
    manual = result.artifacts.get("operating_manual", "")
    assert "main.tf" in manual or "tofu" in manual
