"""Unit tests for AuthorPhase latency runway and progress honesty [REQ-FACT-066, REQ-FACT-067]."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket


@pytest.mark.asyncio
async def test_author_phase_tracks_timeout_error_honestly():
    job = FactoryJob(
        id="fjob_author_test",
        target_agent_id="homelab-admin",
        session_id="sess_author_test",
        seed_intent="Manage infrastructure with opentofu",
        objectives=["Deploy"],
    )

    blueprint_packet = FactoryPacket(
        job_id=job.id,
        packet_type="gap",
        sender_role="blueprint",
        recipient_role="author",
        node_id="blueprint",
        payload={
            "blueprint": {
                "deliverable_type": "tool",
                "tools": [
                    {
                        "name": "manage_homelab_admin",
                        "target_entity": "homelab_admin",
                        "actions": ["status", "deploy"],
                        "description": "Dispatcher for homelab admin",
                    }
                ],
                "skills": [
                    {
                        "id": "manage-opentofu-hyperv",
                        "name": "Manage OpenTofu Hyper-V",
                        "description": "Runbook for managing opentofu",
                    }
                ],
            }
        },
    )

    saved_packets = []
    repo = MagicMock()
    repo.list_packets.return_value = [blueprint_packet]
    repo.save_packet.side_effect = lambda p: saved_packets.append(p)

    # Mock gateway to simulate a TimeoutError
    gateway = MagicMock()
    gateway.default_model_id = "qwen3.8-27b-fp8"
    gateway.complete = AsyncMock(side_effect=asyncio.TimeoutError("Execution exceeded timeout"))

    ctx = PhaseContext(
        job=job,
        repo=repo,
        gateway=gateway,
        wiki=None,
        store=None,
    )

    phase = AuthorPhase()
    result = await phase.run(ctx)

    assert result.outcome in ("ok", "eval")
    # Verify saved author packet payload
    assert len(saved_packets) >= 1
    author_pkt = saved_packets[0]
    payload = author_pkt.payload
    notes = str(payload.get("author_notes", ""))

    # Progress honesty: verify error/timeout is recorded in notes
    assert "timeout" in notes.lower() or "llm failed" in notes.lower() or "error" in notes.lower()


@pytest.mark.asyncio
async def test_phase_llm_json_reports_error_in_fallback():
    from src.application.agent_training_factory.llm import phase_llm_json

    gateway = MagicMock()
    gateway.default_model_id = "test-model"
    gateway.complete = AsyncMock(side_effect=asyncio.TimeoutError("Timed out"))

    fallback = {"tool_code": "print('hello')", "skill_md": "# Runbook", "notes": "seed"}
    res = await phase_llm_json(
        gateway,
        system="System",
        user="User",
        fallback=fallback,
        timeout=0.01,
    )

    assert "error" in res or "seed (LLM failed" in res.get("notes", "")


@pytest.mark.asyncio
async def test_author_phase_decoupled_grounded_project():
    import json

    manifest = {
        "target_directory": "D:\\Projects\\Exprimentation\\Homelab",
        "discovered_binaries": ["powershell.exe", "tofu.exe", "ansible-playbook"],
        "files_tree": [
            {"relative_path": "tofu/blueprints/enterprise-windows-domain/main.tf", "format": "opentofu"},
            {"relative_path": "ansible/playbooks/01_gateway_network.yml", "format": "ansible"},
        ],
    }

    job = FactoryJob(
        id="fjob_author_grounded",
        target_agent_id="homelab-admin",
        session_id="sess_author_grounded",
        seed_intent="Manage homelab infrastructure with OpenTofu and Ansible",
        objectives=["Deploy domain", "Configure network"],
        environment_manifest_json=json.dumps(manifest),
    )

    blueprint_packet = FactoryPacket(
        job_id=job.id,
        packet_type="gap",
        sender_role="blueprint",
        recipient_role="author",
        node_id="blueprint",
        payload={
            "blueprint": {
                "deliverable_type": "native_tool",
                "tools": [
                    {
                        "name": "manage_homelab_admin",
                        "target_entity": "homelab_admin",
                        "actions": ["status", "tofu_plan", "ansible_playbook"],
                        "description": "Dispatcher for homelab admin",
                    }
                ],
                "skills": [
                    {
                        "id": "homelab-infrastructure",
                        "name": "Homelab Infrastructure",
                        "description": "Runbook for managing homelab",
                        "tools": ["manage_homelab_admin"],
                    }
                ],
            }
        },
    )

    saved_packets = []
    repo = MagicMock()
    repo.list_packets.return_value = [blueprint_packet]
    repo.save_packet.side_effect = lambda p: saved_packets.append(p)

    gateway = MagicMock()
    gateway.default_model_id = "test-model"
    # Return valid responses for both decoupled tool and skill calls
    gateway.complete = AsyncMock(
        side_effect=[
            MagicMock(
                content=json.dumps(
                    {
                        "tool_code": "def manage_homelab_admin(action='status', **kwargs): return {'success': True, 'action': action}",
                        "notes": "tool ok",
                    }
                )
            ),
            MagicMock(
                content=json.dumps(
                    {
                        "skill_md": "---\nname: homelab-infrastructure\ndescription: Manage homelab\n---\n# Homelab Infrastructure\n## Overview\nHomelab runbook.\n## Purpose & Scope\nSOP.\n### Objectives\n- Deploy\n## Tools\n- manage_homelab_admin\n## Order\n1. Check\n## Pitfalls\nNone\n## Done-when\nDone"
                    }
                )
            ),
        ]
    )

    ctx = PhaseContext(
        job=job,
        repo=repo,
        gateway=gateway,
        wiki=None,
        store=None,
    )

    phase = AuthorPhase()
    result = await phase.run(ctx)

    assert result.outcome in ("ok", "eval")
    assert gateway.complete.call_count == 2
    assert len(saved_packets) >= 1
    files_map = saved_packets[0].payload.get("files_map", {})
    assert "tools/manage_homelab_admin.py" in files_map
    assert "skills/homelab-infrastructure/SKILL.md" in files_map


@pytest.mark.asyncio
async def test_author_phase_augments_existing_tool_code(tmp_path):
    # Set up existing tool on disk in user pack
    pack_tools_dir = tmp_path / "packs" / "homelab-admin" / "tools"
    pack_tools_dir.mkdir(parents=True)
    existing_tool_file = pack_tools_dir / "manage_homelab_admin.py"
    existing_tool_file.write_text('VALID_ACTIONS = {"status", "tofu_plan", "ansible_playbook"}\n', encoding="utf-8")

    job = FactoryJob(
        id="fjob_augment_test",
        target_agent_id="homelab-admin",
        session_id="sess_augment_test",
        seed_intent="Manage direct Hyper-V VMs",
        objectives=["Start VMs", "Stop VMs"],
        environment_manifest_json=json.dumps(
            {
                "target_directory": "D:\\Projects\\Exprimentation\\Homelab",
                "files_tree": [
                    {"relative_path": "orchestration/providers/HyperVDriver.psm1"},
                ],
            }
        ),
    )

    blueprint_packet = FactoryPacket(
        job_id=job.id,
        packet_type="gap",
        sender_role="blueprint",
        recipient_role="author",
        node_id="blueprint",
        payload={
            "blueprint": {
                "deliverable_type": "native_tool",
                "tools": [
                    {
                        "name": "manage_homelab_admin",
                        "target_entity": "homelab_admin",
                        "actions": ["status", "start_vms", "stop_vms"],
                        "description": "Dispatcher for homelab admin",
                    }
                ],
                "skills": [
                    {
                        "id": "hyperv-direct-orchestration",
                        "name": "Hyper-V Direct Orchestration",
                        "description": "Runbook for direct VM lifecycle",
                        "tools": ["manage_homelab_admin"],
                    }
                ],
            }
        },
    )

    saved_packets = []
    repo = MagicMock()
    repo.list_packets.return_value = [blueprint_packet]
    repo.save_packet.side_effect = lambda p: saved_packets.append(p)

    gateway = MagicMock()
    gateway.default_model_id = "test-model"

    captured_prompts = []

    async def mock_complete(*args, **kwargs):
        messages = kwargs.get("messages", [])
        prompt_text = " ".join(m.get("content", "") for m in messages)
        if args:
            prompt_text += " " + str(args[0])
        captured_prompts.append(prompt_text)
        if len(captured_prompts) == 1:
            return MagicMock(
                content=json.dumps(
                    {
                        "tool_code": "def manage_homelab_admin(action='status', **kwargs): return {'success': True}",
                        "notes": "ok",
                    }
                )
            )
        return MagicMock(
            content=json.dumps(
                {
                    "skill_md": "---\nname: hyperv-direct-orchestration\ndescription: HyperV\n---\n# HyperV\n## Overview\nOverview.\n## Purpose & Scope\nSOP.\n### Objectives\n- Start\n## Tools\n- manage_homelab_admin\n## Order\n1. Check\n## Pitfalls\nNone\n## Done-when\nDone"
                }
            )
        )

    gateway.complete = AsyncMock(side_effect=mock_complete)

    ctx = PhaseContext(
        job=job,
        repo=repo,
        gateway=gateway,
        wiki=None,
        store=None,
    )
    ctx.data_dir = tmp_path

    phase = AuthorPhase()
    result = await phase.run(ctx)

    assert result.outcome in ("ok", "eval")
    # Verify existing tool code was passed to tool authoring prompt
    assert len(captured_prompts) >= 1
    tool_prompt = captured_prompts[0]
    assert "EXISTING TOOL CODE ON DISK" in tool_prompt
    assert "tofu_plan" in tool_prompt
    assert "ansible_playbook" in tool_prompt
