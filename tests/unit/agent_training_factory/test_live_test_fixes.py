"""CARD-171 live-test fixes: objectives persistence, ground heuristics, author/verify quality, preview paths."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from src.application.agent_training_factory.phase import PhaseContext
from src.application.agent_training_factory.phases.author import AuthorPhase
from src.application.agent_training_factory.phases.ground import GroundPhase, _heuristic_manifest, _heuristic_medium
from src.application.agent_training_factory.phases.verify import VerifyPhase
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket, WorkPacket
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

HYPERV_SEED = (
    "unattended Windows 2022 ISO install + autounattend ISO + mount OS ISO + reusable template; "
    "ISO at D:\\Archive\\Tech\\Labs\\installers\\2022.ISO"
)
HYPERV_OBJECTIVES = [
    "Create autounattend ISO for Windows 2022",
    "Mount OS ISO and produce reusable Hyper-V template",
]


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
# A. Persist objectives on FactoryJob
# ---------------------------------------------------------------------------


def test_factory_job_persists_objectives(factory_repo):
    job = FactoryJob(
        id="fjob_obj_persist",
        target_agent_id="hyperv",
        session_id="sess_1",
        status="queued",
        seed_intent=HYPERV_SEED,
        objectives=list(HYPERV_OBJECTIVES),
        current_node_id="ground",
    )
    factory_repo.save_job(job)
    fetched = factory_repo.get_job("fjob_obj_persist")
    assert fetched is not None
    assert fetched.objectives == HYPERV_OBJECTIVES


def test_phase_context_reads_job_objectives_and_work_packet_facts(factory_repo):
    job = FactoryJob(
        id="fjob_ctx_obj",
        target_agent_id="hyperv",
        session_id="sess_1",
        status="queued",
        seed_intent=HYPERV_SEED,
        objectives=["From job field"],
        current_node_id="ground",
    )
    factory_repo.save_job(job)
    work = WorkPacket(
        goal=HYPERV_SEED,
        target_agent_id="hyperv",
        facts=["From work packet facts", "Mount ISO"],
        done_when="ok",
    )
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="orchestrator",
            recipient_role="ground",
            node_id="ground",
            payload=work.model_dump(),
        )
    )
    ctx = PhaseContext(job=factory_repo.get_job(job.id), repo=factory_repo)
    objs = ctx.objectives
    assert "From job field" in objs
    assert "From work packet facts" in objs
    assert "Mount ISO" in objs


@pytest.mark.asyncio
async def test_create_job_api_copies_objectives_onto_job(tmp_path, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from src.web.app import create_app

    data_dir = tmp_path / "data"
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))

    store = SQLiteStateStore(db_path=str(db_path))
    app = create_app(state_store=store)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/agent_training_factory/jobs",
            json={
                "target_agent_id": "hyperv",
                "seed_intent": HYPERV_SEED,
                "objectives": HYPERV_OBJECTIVES,
                "risk_policy": "ask",
            },
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]
        get_resp = await ac.get(f"/api/agent_training_factory/jobs/{job_id}")
        job = get_resp.json()["job"]
        assert job["objectives"] == HYPERV_OBJECTIVES


# ---------------------------------------------------------------------------
# B. Ground heuristics + rich manual
# ---------------------------------------------------------------------------


def test_heuristic_medium_matches_hyperv_without_hyphen():
    combined = "hyperv unattend windows 2022 iso autounattend template vhdx"
    assert _heuristic_medium(combined) == "cli"


def test_heuristic_manifest_includes_hyperv_module_for_hyperv_slug():
    job = FactoryJob(
        id="fjob_h",
        target_agent_id="hyperv",
        session_id="s",
        seed_intent=HYPERV_SEED,
        objectives=HYPERV_OBJECTIVES,
    )
    combined = f"{job.target_agent_id} {job.seed_intent} {' '.join(job.objectives)}".lower()
    medium = _heuristic_medium(combined)
    manifest = _heuristic_manifest(job, "hyperv", medium, combined)
    assert medium == "cli"
    assert "Hyper-V" in manifest["discovered_modules"]
    assert "powershell.exe" in manifest["discovered_binaries"]


@pytest.mark.asyncio
async def test_ground_hyperv_unattend_iso_path_in_manual(factory_repo):
    job = FactoryJob(
        id="fjob_ground_hyperv",
        target_agent_id="hyperv",
        session_id="sess_g",
        status="running",
        seed_intent=HYPERV_SEED,
        objectives=list(HYPERV_OBJECTIVES),
        current_node_id="ground",
    )
    factory_repo.save_job(job)
    wiki = MagicMock()
    wiki.create_note.side_effect = lambda **kwargs: {
        "path": f"wiki/{kwargs.get('title', 'note').replace(' ', '_')}.md",
        "content": kwargs.get("content", ""),
    }
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None, wiki=wiki)
    result = await GroundPhase().run(ctx)
    assert result.outcome == "ok"
    manifest = result.artifacts["manifest"]
    assert manifest["target_medium"] == "cli"
    assert "Hyper-V" in manifest["discovered_modules"]
    # operating manual must include ISO path text (from fallback or wiki write)
    note_calls = wiki.create_note.call_args_list
    manuals = [c.kwargs.get("content", "") for c in note_calls]
    joined = "\n".join(manuals)
    assert "2022.ISO" in joined or "installers" in joined.lower()
    assert "unattend" in joined.lower() or "autounattend" in joined.lower()
    assert HYPERV_SEED[:40] in joined or "Windows 2022" in joined


# ---------------------------------------------------------------------------
# C. Author quality gate
# ---------------------------------------------------------------------------


STUB_SKILL = """---
name: Hyperv Automation
description: Agent for managing hyperv tasks
tools:
  - manage_hyperv
---

# Hyperv Runbook

Agent for managing hyperv tasks.
"""


@pytest.mark.asyncio
async def test_author_hyperv_unattend_skill_encodes_objectives(factory_repo):
    job = FactoryJob(
        id="fjob_author_hv",
        target_agent_id="hyperv",
        session_id="sess_a",
        status="running",
        seed_intent=HYPERV_SEED,
        objectives=list(HYPERV_OBJECTIVES),
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
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    result = await AuthorPhase().run(ctx)
    assert result.outcome == "ok"
    files_map = result.artifacts["files_map"]
    skill = files_map.get("skills/hyperv/SKILL.md", "")
    assert "## Purpose" in skill or "## Purpose" in skill.replace("\r", "")
    assert "Objectives" in skill
    assert "unattend" in skill.lower() or "iso" in skill.lower()
    assert "Agent for managing" not in skill or "2022.ISO" in skill
    # Must quote seed brief / path somehow
    assert "2022.ISO" in skill or "ISO" in skill
    tool = files_map.get("tools/manage_hyperv.py", "") + files_map.get("tools/manage_hyperv.ps1", "")
    assert any(k in tool.lower() for k in ("unattend", "iso", "template", "vhdx", "hyper-v", "new-vm"))


# ---------------------------------------------------------------------------
# D. Verify shallow-stub failure
# ---------------------------------------------------------------------------


def test_verification_rejects_stub_skill_when_seed_has_objective_keywords():
    from src.application.orchestration.verification_battery import is_shallow_stub_artifact

    assert is_shallow_stub_artifact(
        skill_md=STUB_SKILL,
        tool_code="def manage_hyperv(action='status', **kwargs): return {'success': True}",
        seed_intent=HYPERV_SEED,
        objectives=HYPERV_OBJECTIVES,
    )


def test_verification_accepts_rich_skill_with_objective_keywords():
    from src.application.orchestration.verification_battery import is_shallow_stub_artifact

    rich = """---
name: Hyper-V Unattend Installer
description: Unattended Windows 2022 ISO install with autounattend and reusable template
tools:
  - manage_hyperv
---

# Hyper-V Unattend Runbook

## Purpose
unattended Windows 2022 ISO install + autounattend ISO + mount OS ISO + reusable template;
ISO at D:\\\\Archive\\\\Tech\\\\Labs\\\\installers\\\\2022.ISO

## Objectives
- Create autounattend ISO for Windows 2022
- Mount OS ISO and produce reusable Hyper-V template

## Available Actions
- status / list
- create
"""
    tool = '''
def manage_hyperv(action="status", dry_run=False, **kwargs):
    """Handles unattend ISO mount and Hyper-V template creation."""
    valid_actions = ["status", "list", "create", "get"]
    if action not in valid_actions:
        raise ValueError("bad")
    return {"success": True, "action": action, "unattend": True, "iso": "2022.ISO"}
'''
    assert not is_shallow_stub_artifact(
        skill_md=rich,
        tool_code=tool,
        seed_intent=HYPERV_SEED,
        objectives=HYPERV_OBJECTIVES,
    )


@pytest.mark.asyncio
async def test_verify_phase_fails_on_stub_skill(factory_repo):
    job = FactoryJob(
        id="fjob_verify_stub",
        target_agent_id="hyperv",
        session_id="sess_v",
        status="running",
        seed_intent=HYPERV_SEED,
        objectives=list(HYPERV_OBJECTIVES),
        current_node_id="verify",
    )
    factory_repo.save_job(job)
    factory_repo.save_packet(
        FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="author",
            recipient_role="verify",
            node_id="author",
            payload={
                "tool_name": "manage_hyperv",
                "files_map": {
                    "tools/manage_hyperv.py": (
                        "def manage_hyperv(action='status', dry_run=False, **kwargs):\n"
                        "    valid_actions = ['status', 'list']\n"
                        "    if action not in valid_actions: raise ValueError('bad')\n"
                        "    return {'success': True, 'action': action}\n"
                    ),
                    "skills/hyperv/SKILL.md": STUB_SKILL,
                },
            },
        )
    )
    ctx = PhaseContext(job=job, repo=factory_repo, gateway=None)
    result = await VerifyPhase().run(ctx)
    assert result.outcome == "fail"

def test_tool_mismatches_domain_services_vs_hyperv():
    from src.application.agent_training_factory.phases.author import _tool_mismatches_domain

    hyperv_tool = "Import-Module Hyper-V\nHyper-V\\Get-VM | ConvertTo-Json"
    services_tool = "Get-Service | Select-Object Name, Status"
    intent = "List Windows services status for operators"
    assert _tool_mismatches_domain(hyperv_tool, intent, ["List Windows services"], "win-svc") is True
    assert _tool_mismatches_domain(services_tool, intent, ["List Windows services"], "win-svc") is False
    hv_intent = "Manage Hyper-V VMs with unattend ISO"
    assert _tool_mismatches_domain(hyperv_tool, hv_intent, ["Create VM"], "hyperv") is False


@pytest.mark.asyncio
async def test_author_rejects_hyperv_bleed_on_services_brief(monkeypatch):
    """CARD-171: Author must keep Get-Service seed when LLM returns Hyper-V costume."""
    from src.application.agent_training_factory.phases.author import AuthorPhase
    from src.application.agent_training_factory.phase import PhaseContext
    from src.domain.orchestration.factory_packets import FactoryJob

    class FakeRepo:
        def __init__(self):
            self.packets = []
        def list_packets(self, job_id):
            return list(self.packets)
        def save_packet(self, packet):
            self.packets.append(packet)

    job = FactoryJob(
        id="fjob_test_svc",
        target_agent_id="win-svc-atf2",
        session_id="sess",
        status="running",
        seed_intent="Build a Windows sysadmin CLI agent that lists Windows services and reports Status, StartType, and DisplayName.",
        objectives=["List all Windows services with Status, StartType, and DisplayName"],
        current_node_id="author",
    )
    repo = FakeRepo()
    ctx = PhaseContext(job=job, repo=repo, gateway=None, wiki=None, store=None, data_dir=None, battery=None)

    async def fake_llm(*args, **kwargs):
        return {
            "tool_code": "def manage_win_svc_atf2(action='status', dry_run=False):\n    # Hyper-V\\Get-VM costume\n    return {'success': True, 'action': action}\n",
            "skill_md": "---\nname: x\ndescription: yyy\n---\n\n## Purpose\nBuild a Windows sysadmin CLI agent that lists Windows services and reports Status, StartType, and DisplayName.\n\n## Objectives\n- List all Windows services with Status, StartType, and DisplayName\n\n## Available Actions\n- status: Inspect running virtual machines\n",
            "notes": "llm hyperv bleed",
        }

    monkeypatch.setattr(
        "src.application.agent_training_factory.phases.author.phase_llm_json",
        fake_llm,
    )
    result = await AuthorPhase().run(ctx)
    assert result.outcome == "ok"
    files = result.artifacts["files_map"]
    tool = files["tools/manage_win_svc_atf2.py"]
    skill = files["skills/win_svc_atf2/SKILL.md"]
    assert "Get-Service" in tool
    assert "Get-VM" not in tool.replace("\\\\", "\\") and "Hyper-V\\Get-VM" not in tool
    assert "virtual machine" not in skill.lower()
