"""CARD-171 follow-up: max verify rinse, path safety false-positive, fail reasons visible."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from src.application.agent_training_factory.orchestrator import FactoryOrchestrator
from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.application.agent_training_factory.phases.verify import VerifyPhase
from src.application.agent_training_factory.registry import (
    PHASE_AUTHOR,
    PHASE_VERIFY,
)
from src.application.orchestration.verification_battery import (
    VerificationBatteryService,
    detect_path_safety_violation,
)
from src.domain.orchestration.factory_packets import (
    EvalPacket,
    FactoryJob,
    FactoryPacket,
)
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

HYPERV_SEED = (
    "unattended Windows 2022 ISO install + autounattend ISO + mount OS ISO + reusable template; "
    "ISO at D:\\Archive\\Tech\\Labs\\installers\\2022.ISO"
)


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


# ---------------------------------------------------------------------------
# Path safety: Windows abs paths OK; traversal still blocked
# ---------------------------------------------------------------------------


def test_detect_path_allows_windows_absolute_archive_iso():
    code = '''
def manage_hyperv(action="create", iso_path=r"D:\\Archive\\Tech\\Labs\\installers\\2022.ISO", **kwargs):
    return {"success": True, "iso": iso_path}
'''
    assert detect_path_safety_violation(code) is None


def test_detect_path_allows_c_users_style_paths():
    code = 'root = "C:\\\\Users\\\\jacob\\\\Labs\\\\unattend.xml"\n'
    assert detect_path_safety_violation(code) is None


def test_detect_path_blocks_dotdot_traversal():
    code = 'open("..\\\\..\\\\etc\\\\passwd")'
    reason = detect_path_safety_violation(code)
    assert reason is not None
    assert "traversal" in reason.lower() or ".." in reason


def test_detect_path_blocks_unix_etc_literal():
    code = 'open("/etc/shadow")'
    reason = detect_path_safety_violation(code)
    assert reason is not None


@pytest.mark.asyncio
async def test_battery_does_not_fail_solely_for_windows_iso_path(factory_repo):
    """Regression: D:\\Archive\\...\\2022.ISO must not trip stage-2 preflight."""
    battery = VerificationBatteryService(runner=MagicMock())
    tool = '''
def manage_hyperv(action="status", dry_run=False, **kwargs):
    iso = r"D:\\Archive\\Tech\\Labs\\installers\\2022.ISO"
    valid_actions = ["status", "list", "create"]
    if action not in valid_actions:
        raise ValueError("bad")
    return {"success": True, "action": action, "iso": iso, "unattend": True}
'''
    # Avoid full sandbox: only assert preflight helper + early battery path check
    assert detect_path_safety_violation(tool) is None
    # Shallow stub gate off by omitting skill_content objectives mismatch
    skill = """---
name: Hyper-V
description: Unattended Windows 2022 ISO install with autounattend template
tools:
  - manage_hyperv
---

# Runbook

## Purpose
unattended Windows 2022 ISO install + autounattend ISO + mount OS ISO + reusable template;
ISO at D:\\\\Archive\\\\Tech\\\\Labs\\\\installers\\\\2022.ISO

## Objectives
- Create autounattend ISO for Windows 2022
- Mount OS ISO and produce reusable Hyper-V template

## Available Actions
- status
- list
- create
"""
    # Mock runner so we only care that path preflight does not abort first
    async def _ok(**kwargs):
        class R:
            exit_code = 0
            stdout = "ok"
            stderr = ""
            error = None
        return R()

    battery.runner.run_tool_test = _ok  # type: ignore
    res = await battery.run_battery(
        tool_code=tool,
        test_code="from tool import manage_hyperv\nassert manage_hyperv()['success']",
        skill_content=skill,
        seed_intent=HYPERV_SEED,
        objectives=["Create autounattend ISO for Windows 2022"],
        repeats=1,
    )
    # Must not fail at stage-2 preflight for the Windows path alone
    assert "C:\\" not in (res.critic_notes or "") or res.passed
    assert "Path traversal pattern detected" not in (res.critic_notes or "")
    assert res.passed is True


# ---------------------------------------------------------------------------
# Max verify rinses
# ---------------------------------------------------------------------------


class AlwaysFailBattery:
    async def run_battery(self, **kwargs):
        return EvalPacket(
            checks_executed=["stage_2_safety"],
            passed=False,
            stage_1_functional=False,
            stage_2_safety=False,
            stage_3_idempotency=False,
            stage_4_critic=False,
            critic_notes="Safety Guardrail Alert: simulated fail for rinse test",
            duration_ms=1.0,
        )


def _author_packet(job_id: str) -> FactoryPacket:
    return FactoryPacket(
        job_id=job_id,
        packet_type="work",
        sender_role="author",
        recipient_role="verify",
        node_id=PHASE_AUTHOR,
        payload={
            "tool_name": "manage_hyperv",
            "files_map": {
                "tools/manage_hyperv.py": (
                    "def manage_hyperv(action='status', dry_run=False, **kwargs):\n"
                    "    return {'success': True, 'action': action, 'iso': r'D:\\\\Archive\\\\x.ISO'}\n"
                ),
                "skills/hyperv/SKILL.md": (
                    "---\nname: Hyper-V\ndescription: unattend ISO template\ntools:\n  - manage_hyperv\n---\n\n"
                    "# Runbook\n\n## Purpose\nunattend ISO template\n\n## Objectives\n- iso\n"
                ),
            },
            "message": "Author produced manage_hyperv",
        },
    )


@pytest.mark.asyncio
async def test_verify_increments_rinse_and_exhausts_at_max(factory_repo):
    job = FactoryJob(
        id="fjob_rinse_max",
        target_agent_id="hyperv",
        session_id="sess_r",
        status="running",
        seed_intent=HYPERV_SEED,
        objectives=["Create autounattend ISO"],
        current_node_id=PHASE_VERIFY,
        verify_rinse_count=0,
        max_verify_rinses=3,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_author_packet(job.id))

    battery = AlwaysFailBattery()
    orch = FactoryOrchestrator(repo=factory_repo, battery_service=battery, poll_interval=0.01)

    # Fail 1 -> rinse to author (count=1)
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j is not None
    assert j.verify_rinse_count == 1
    assert j.status == "running"
    assert j.current_node_id == PHASE_AUTHOR

    # Author would normally run; force back to verify for hermetic rinse test
    factory_repo.update_job_status(job.id, "running", current_node_id=PHASE_VERIFY)
    factory_repo.save_packet(_author_packet(job.id))

    # Fail 2
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j.verify_rinse_count == 2
    assert j.current_node_id == PHASE_AUTHOR

    factory_repo.update_job_status(job.id, "running", current_node_id=PHASE_VERIFY)
    factory_repo.save_packet(_author_packet(job.id))

    # Fail 3 -> terminal failed, no more rinse
    await orch.step_job(job.id)
    j = factory_repo.get_job(job.id)
    assert j.verify_rinse_count == 3
    assert j.status == "failed"
    assert j.current_node_id in ("failed", PHASE_VERIFY) or j.status == "failed"

    packets = factory_repo.list_packets(job.id)
    terminal = [p for p in packets if p.sender_role == "verify" and p.payload.get("terminal_fail")]
    assert terminal, "expected terminal fail packet"
    notes = terminal[-1].payload.get("critic_notes") or ""
    assert "simulated fail" in notes.lower()
    msg = terminal[-1].payload.get("message") or ""
    assert "simulated fail" in msg.lower() or "critic" in msg.lower() or "rinse" in msg.lower()


@pytest.mark.asyncio
async def test_verify_packet_includes_critic_notes_and_rinse_progress(factory_repo):
    job = FactoryJob(
        id="fjob_rinse_msg",
        target_agent_id="hyperv",
        session_id="sess_m",
        status="running",
        seed_intent=HYPERV_SEED,
        current_node_id=PHASE_VERIFY,
        verify_rinse_count=0,
        max_verify_rinses=3,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(_author_packet(job.id))
    ctx = PhaseContext(job=job, repo=factory_repo, battery=AlwaysFailBattery())
    result = await VerifyPhase().run(ctx)
    assert result.outcome == "fail"
    pkts = [p for p in factory_repo.list_packets(job.id) if p.sender_role == "verify"]
    assert pkts
    payload = pkts[-1].payload
    assert "simulated fail" in (payload.get("critic_notes") or "").lower()
    assert payload.get("verify_rinse_count") == 1
    assert "1/3" in (payload.get("message") or "") or "rinse" in (payload.get("message") or "").lower()


# ---------------------------------------------------------------------------
# Author sees last verify failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_author_user_prompt_includes_last_critic_notes(factory_repo, monkeypatch):
    job = FactoryJob(
        id="fjob_author_notes",
        target_agent_id="hyperv",
        session_id="sess_a",
        status="running",
        seed_intent=HYPERV_SEED,
        objectives=["Create autounattend ISO"],
        current_node_id=PHASE_AUTHOR,
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="eval",
            sender_role="verify",
            recipient_role="author",
            node_id=PHASE_VERIFY,
            payload={
                "message": "Verify battery FAILED",
                "passed": False,
                "critic_notes": "Safety Guardrail Alert: Path traversal pattern detected",
            },
        )
    )

    captured: Dict[str, Any] = {}

    async def _fake_llm(gateway, system, user, fallback, max_tokens=0, timeout=0):
        captured["user"] = user
        return fallback

    monkeypatch.setattr(
        "src.application.agent_training_factory.phases.author.phase_llm_json",
        _fake_llm,
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    await AuthorPhase().run(ctx)
    assert "LAST VERIFY" in captured["user"] and "FAILURE" in captured["user"]
    assert "Path traversal" in captured["user"] or "Safety Guardrail" in captured["user"]


# ---------------------------------------------------------------------------
# FactoryJob persistence of rinse fields
# ---------------------------------------------------------------------------


def test_factory_job_persists_verify_rinse_fields(factory_repo):
    job = FactoryJob(
        id="fjob_rinse_persist",
        target_agent_id="hyperv",
        session_id="sess_p",
        status="queued",
        seed_intent="x",
        verify_rinse_count=2,
        max_verify_rinses=5,
        current_node_id="ground",
    )
    factory_repo.save_job(job)
    fetched = factory_repo.get_job("fjob_rinse_persist")
    assert fetched is not None
    assert fetched.verify_rinse_count == 2
    assert fetched.max_verify_rinses == 5
