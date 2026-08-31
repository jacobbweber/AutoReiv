"""
ACE-style online playbook notes + snapshot/rollback [REQ-IMPROVE-001 - REQ-IMPROVE-006] [REQ-IMPROVE-016].
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.ace_online import (
    GENERATOR_ROLE,
    propose_notes_into_skill,
    record_failed_turn_delta,
    record_sidecar_note,
    reflect_failed_turn,
)
from src.application.orchestration.skill_proposals import (
    PYTHON_BUILTIN_NOTE,
    apply_skill_proposal_decision,
    commit_skill_pack,
)
from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.application.skills.user_catalog import UserSkillCatalog
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role
from src.domain.kernel.models import AgentProfile, AgentTone
from src.domain.orchestration.models import ProposalKind, ProposalStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.kernel.test_agent_kernel import MockScriptedLLM

SRC_SKILLS = Path(__file__).resolve().parents[3] / "src" / "application" / "skills"

PACK_MD = """---
name: okta-admin
description: Homelab Okta admin playbook.
---

# Okta admin

List users. Reset/unlock is a stub, not a live API.
"""


@pytest.fixture
def env(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "test_state.db")
    store.initialize_db()
    data_dir = tmp_path / "data"
    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True)
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    catalog.save_pack("okta-admin", "okta-admin", "Homelab Okta admin playbook.", "List users. Stub reset.")
    other = catalog.save_pack("other-pack", "other-pack", "Untouched sibling pack.", "Do not touch.")
    assert other["success"] is True
    return {
        "tmp": tmp_path,
        "store": store,
        "data_dir": data_dir,
        "skills_dir": skills_dir,
        "catalog": catalog,
        "skill_path": skills_dir / "okta-admin" / "SKILL.md",
        "other_path": skills_dir / "other-pack" / "SKILL.md",
        "src_before": {p.name: p.stat().st_mtime_ns for p in SRC_SKILLS.glob("*.py")},
    }


def _src_untouched(env) -> None:
    after = {p.name: p.stat().st_mtime_ns for p in SRC_SKILLS.glob("*.py")}
    assert after == env["src_before"]


def test_generator_is_existing_kernel_not_langgraph():
    ace_src = Path("src/application/orchestration/ace_online.py").read_text(encoding="utf-8")
    kernel_src = Path("src/application/kernel/agent_kernel.py").read_text(encoding="utf-8")
    assert GENERATOR_ROLE == "AgentKernel"
    assert "import langgraph" not in ace_src
    assert "from langgraph" not in ace_src
    assert "import skillopt" not in ace_src
    assert "AgentKernel" in kernel_src
    assert "record_failed_turn_delta" in kernel_src
    assert "class AceKernel" not in ace_src
    assert "class AceBuilder" not in ace_src


def test_snapshot_then_rollback_restores_bytes(env):
    catalog = env["catalog"]
    skill_path = env["skill_path"]
    original = skill_path.read_bytes()
    notes_path = env["skills_dir"] / "okta-admin" / "PLAYBOOK_NOTES.md"
    notes_path.write_text("- keep me\n", encoding="utf-8")
    notes_bytes = notes_path.read_bytes()
    other_bytes = env["other_path"].read_bytes()

    snap = catalog.snapshot_pack("okta-admin")
    assert snap["success"] is True
    assert snap["snapshot_id"]
    snap_dir = env["skills_dir"] / "okta-admin" / "snapshots" / snap["snapshot_id"]
    assert (snap_dir / "SKILL.md").is_file()

    skill_path.write_text(PACK_MD + "\n\nMUTATED\n", encoding="utf-8")
    notes_path.write_text("- mutated\n", encoding="utf-8")
    assert skill_path.read_bytes() != original

    rolled = catalog.rollback_pack("okta-admin", snap["snapshot_id"])
    assert rolled["success"] is True
    assert skill_path.read_bytes() == original
    assert notes_path.read_bytes() == notes_bytes
    assert env["other_path"].read_bytes() == other_bytes
    _src_untouched(env)


def test_snapshot_failure_skips_sidecar_append(env, monkeypatch):
    catalog = env["catalog"]
    skill_before = env["skill_path"].read_bytes()
    monkeypatch.setattr(catalog, "snapshot_pack", lambda pack_id: {"success": False, "error": "disk full"})
    result = catalog.append_playbook_note("okta-admin", insight="should not land")
    assert result["success"] is False
    notes = env["skills_dir"] / "okta-admin" / "PLAYBOOK_NOTES.md"
    jsonl = env["skills_dir"] / "okta-admin" / "notes.jsonl"
    assert not notes.exists()
    assert not jsonl.exists()
    assert env["skill_path"].read_bytes() == skill_before


def test_failed_turn_creates_draft_proposal_not_silent_skill_md_edit(env):
    skill_before = env["skill_path"].read_bytes()
    result = record_failed_turn_delta(
        env["store"],
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        session_id="sess_ace",
        agent_id="assistant",
        error_message="okta_reset_or_unlock returned playbook stub",
        tool_errors=[{"tool_name": "okta_reset_or_unlock", "error": "playbook stub"}],
        catalog=env["catalog"],
    )
    assert result["deltas"] == 1
    assert result["status"] == "draft"
    assert result["kind"] == "skill"
    assert result["ace_delta"] is True
    assert result["skill_md_written"] is False
    assert result["disk_written"] is False
    assert result["nightly_enqueued"] is False
    assert env["skill_path"].read_bytes() == skill_before

    proposal = env["store"].get_proposal(result["proposal_id"])
    assert proposal.kind == ProposalKind.SKILL
    assert proposal.status == ProposalStatus.DRAFT
    payload = json.loads(proposal.payload_json)
    assert payload["ace_delta"] is True
    assert payload["snapshot_id"]
    assert "okta_reset_or_unlock" in payload["why"] or "okta_reset_or_unlock" in payload["how"]
    # not a full playbook rewrite
    assert "# Okta admin" not in payload["how"] or payload["how"].count("\n") < 20

    pending = env["store"].get_pending_approvals(session_id="sess_ace")
    assert any(row["tool_name"] == "propose_skill" for row in pending)
    assert not (env["tmp"] / "routines.json").exists()
    _src_untouched(env)


def test_successful_turn_does_not_rewrite_skill_md(env):
    skill_before = env["skill_path"].read_bytes()
    catalog = env["catalog"]
    # Reflector on success is optional; curator must not rewrite SKILL.md.
    insight = reflect_failed_turn(pack_id="okta-admin", error_message=None, tool_errors=[])
    assert insight["insight"]
    assert env["skill_path"].read_bytes() == skill_before
    assert catalog.read_pack("okta-admin")["instructions"]
    _src_untouched(env)


def test_python_shaped_delta_stays_propose_tool_draft(env):
    skill_before = env["skill_path"].read_bytes()
    result = record_failed_turn_delta(
        env["store"],
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        session_id="sess_py",
        agent_id="assistant",
        error_message="Need a Python BuiltinSkill module under src/application/skills/okta_skill.py",
        catalog=env["catalog"],
    )
    assert result["kind"] == "tool"
    assert result["status"] == "draft"
    assert result["python_builtin_note"] == PYTHON_BUILTIN_NOTE
    assert result["skill_md_written"] is False
    assert env["skill_path"].read_bytes() == skill_before
    assert not (SRC_SKILLS / "okta_skill.py").exists()
    decided = apply_skill_proposal_decision(
        env["store"], proposal_id=result["proposal_id"], decision="approved"
    )
    assert decided["disk_written"] is False
    _src_untouched(env)


def test_sidecar_append_only_does_not_modify_skill_md(env):
    skill_before = env["skill_path"].read_bytes()
    first = record_sidecar_note(
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        insight="first breadcrumb",
        evidence="tool stub",
        session_id="sess_n",
        catalog=env["catalog"],
    )
    assert first["success"] is True
    md = env["skills_dir"] / "okta-admin" / "PLAYBOOK_NOTES.md"
    jsonl = env["skills_dir"] / "okta-admin" / "notes.jsonl"
    md_after_first = md.read_text(encoding="utf-8")
    jsonl_after_first = jsonl.read_text(encoding="utf-8")
    second = record_sidecar_note(
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        insight="second breadcrumb",
        catalog=env["catalog"],
    )
    assert second["success"] is True
    md_after = md.read_text(encoding="utf-8")
    jsonl_after = jsonl.read_text(encoding="utf-8")
    assert md_after.startswith(md_after_first)
    assert jsonl_after.startswith(jsonl_after_first)
    assert "first breadcrumb" in md_after
    assert "second breadcrumb" in md_after
    assert env["skill_path"].read_bytes() == skill_before
    lines = [ln for ln in jsonl_after.splitlines() if ln.strip()]
    assert len(lines) == 2
    # promotion is still propose_skill
    promo = propose_notes_into_skill(
        env["store"],
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        session_id="sess_n",
        agent_id="assistant",
        catalog=env["catalog"],
    )
    assert promo["status"] == "draft"
    assert env["skill_path"].read_bytes() == skill_before
    _src_untouched(env)


def test_snapshots_are_not_listed_as_live_packs(env):
    env["catalog"].snapshot_pack("okta-admin")
    ids = {m.id for m in env["catalog"].list_manifests()}
    assert "okta-admin" in ids
    assert "other-pack" in ids
    assert all("snapshots" not in i for i in ids)
    loader_ids = {m.id for m in DynamicSkillLoader.list_skill_manifests(str(env["skills_dir"]))}
    assert all("snapshots" not in i for i in loader_ids)


def test_commit_snapshots_before_apply_and_rollback_restores(env):
    skill_before = env["skill_path"].read_bytes()
    drafted = record_failed_turn_delta(
        env["store"],
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        session_id="sess_c",
        agent_id="agent-builder",
        error_message="checker miss",
        catalog=env["catalog"],
    )
    apply_skill_proposal_decision(env["store"], proposal_id=drafted["proposal_id"], decision="approved")
    committed = commit_skill_pack(
        env["store"],
        proposal_id=drafted["proposal_id"],
        data_dir=env["data_dir"],
        catalog=env["catalog"],
        overwrite=True,
    )
    assert committed["disk_written"] is True
    assert committed["src_written"] is False
    assert env["skill_path"].read_bytes() != skill_before
    rolled = env["catalog"].rollback_pack("okta-admin", committed["snapshot_id"])
    assert rolled["success"] is True
    assert env["skill_path"].read_bytes() == skill_before
    _src_untouched(env)


def test_commit_skips_apply_when_snapshot_fails(env, monkeypatch):
    skill_before = env["skill_path"].read_bytes()
    drafted = record_failed_turn_delta(
        env["store"],
        pack_id="okta-admin",
        data_dir=env["data_dir"],
        session_id="sess_fail",
        agent_id="agent-builder",
        error_message="checker miss",
        catalog=env["catalog"],
    )
    apply_skill_proposal_decision(env["store"], proposal_id=drafted["proposal_id"], decision="approved")
    monkeypatch.setattr(env["catalog"], "snapshot_pack", lambda pack_id: {"success": False, "error": "io"})
    result = commit_skill_pack(
        env["store"],
        proposal_id=drafted["proposal_id"],
        data_dir=env["data_dir"],
        catalog=env["catalog"],
        overwrite=True,
    )
    assert result["success"] is False
    assert result["disk_written"] is False
    assert "Snapshot failed" in result["error"] or "io" in result["error"]
    assert env["skill_path"].read_bytes() == skill_before


@pytest.mark.asyncio
async def test_kernel_failed_turn_parks_one_draft(env):
    class BoomLLM(MockScriptedLLM):
        async def complete(self, request):
            raise RuntimeError("provider down")

    llm = BoomLLM(responses=[])
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    registry = ScopedToolRegistry()
    collector = TelemetryCollector(store=env["store"])
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=env["store"],
        telemetry=collector,
        data_dir=str(env["data_dir"]),
        user_skill_catalog=env["catalog"],
    )
    kernel.ace_pack_id = "okta-admin"
    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="t",
        system_prompt="x",
        tone=AgentTone.FRIENDLY,
        allowed_tool_names=[],
    )
    session = env["store"].create_session(agent_id=profile.id, title="ace fail")
    skill_before = env["skill_path"].read_bytes()
    with pytest.raises(Exception, match="provider down"):
        await kernel.run_turn(agent=profile, session_id=session.id, user_content="reset okta user")

    conn = env["store"]._get_connection()
    try:
        rows = conn.execute("SELECT id, kind, status, payload_json FROM proposals").fetchall()
    finally:
        if env["store"]._mem_conn is None:
            conn.close()
    assert len(rows) == 1
    payload = json.loads(rows[0][3] if not hasattr(rows[0], "keys") else rows[0]["payload_json"])
    # sqlite row may be tuple
    if not isinstance(payload, dict):
        payload = json.loads(rows[0][3])
    assert payload.get("ace_delta") is True
    assert env["skill_path"].read_bytes() == skill_before
    _src_untouched(env)


@pytest.mark.asyncio
async def test_kernel_success_does_not_write_skill_md(env):
    llm = MockScriptedLLM(
        responses=[
            CompletionResponse(
                model="mock/model",
                message=ChatMessage(role=Role.ASSISTANT, content="All good."),
                finish_reason="stop",
            )
        ]
    )
    gateway = MultiProviderGateway()
    gateway.register_provider(llm)
    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=ScopedToolRegistry(),
        state_store=env["store"],
        telemetry=TelemetryCollector(store=env["store"]),
        data_dir=str(env["data_dir"]),
        user_skill_catalog=env["catalog"],
    )
    kernel.ace_pack_id = "okta-admin"
    profile = AgentProfile(
        id="assistant",
        name="Assistant",
        description="t",
        system_prompt="x",
        tone=AgentTone.FRIENDLY,
        allowed_tool_names=[],
    )
    session = env["store"].create_session(agent_id=profile.id, title="ace ok")
    skill_before = env["skill_path"].read_bytes()
    msg = await kernel.run_turn(agent=profile, session_id=session.id, user_content="hello")
    assert "All good" in (msg.content or "")
    assert env["skill_path"].read_bytes() == skill_before
    conn = env["store"]._get_connection()
    try:
        rows = conn.execute("SELECT id FROM proposals").fetchall()
    finally:
        if env["store"]._mem_conn is None:
            conn.close()
    assert rows == []
