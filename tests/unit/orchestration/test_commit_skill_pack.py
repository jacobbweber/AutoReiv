"""
commit_skill_pack writes approved proposals via UserSkillCatalog [REQ-BUILD-012 - REQ-BUILD-014].
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.orchestration.skill_proposals import (
    apply_skill_proposal_decision,
    commit_skill_pack,
    propose_skill,
    propose_tool,
    propose_workflow,
)
from src.application.skills.agent_builder_skill import AgentBuilderSkill
from src.application.skills.user_catalog import UserSkillCatalog
from src.domain.agents.profiles import AGENT_BUILDER_PROFILE, CODING_PROFILE
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def setup(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "test_state.db")
    data_dir = tmp_path / "data"
    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True)
    registry = BuiltinAgentRegistry(state_store=store)
    catalog = UserSkillCatalog(skills_dir=skills_dir)
    skill = AgentBuilderSkill(
        agent_registry=registry,
        tool_registry=ScopedToolRegistry(),
        store=store,
        data_dir=data_dir,
    )
    src_skills = Path(__file__).resolve().parents[3] / "src" / "application" / "skills"
    return {
        "store": store,
        "data_dir": data_dir,
        "skills_dir": skills_dir,
        "registry": registry,
        "catalog": catalog,
        "skill": skill,
        "src_skills": src_skills,
        "src_before": {p.name: p.stat().st_mtime_ns for p in src_skills.glob("*.py")},
    }


def _src_untouched(setup) -> None:
    after = {p.name: p.stat().st_mtime_ns for p in setup["src_skills"].glob("*.py")}
    assert after == setup["src_before"]


def _approve(setup, created):
    decided = apply_skill_proposal_decision(
        setup["store"],
        proposal_id=created["proposal_id"],
        decision="approved",
    )
    assert decided["status"] == "approved"
    assert decided["disk_written"] is False
    return decided


def test_approve_then_commit_writes_skill_md(setup):
    created = propose_skill(
        setup["store"],
        what="Homelab backup playbook",
        why="Operator needs a documented backup SOP",
        how="1. Confirm the host.\n2. Run the backup.\n3. Verify the archive.",
        where="skills/homelab-backup/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="agent-builder",
        prefer_existing_agent_id="review",
    )
    _approve(setup, created)
    dest = setup["skills_dir"] / "homelab-backup" / "SKILL.md"
    assert not dest.exists()

    result = commit_skill_pack(
        setup["store"],
        proposal_id=created["proposal_id"],
        data_dir=setup["data_dir"],
        catalog=setup["catalog"],
        agent_registry=setup["registry"],
    )
    assert result["success"] is True
    assert result["disk_written"] is True
    assert result["src_written"] is False
    assert dest.is_file()
    body = dest.read_text(encoding="utf-8")
    assert "name: homelab-backup" in body
    assert "Homelab backup playbook" in body or "Operator needs" in body
    opened = setup["catalog"].read_pack("homelab-backup")
    assert opened["success"] is True
    assert opened["manifest"]["id"] == "homelab-backup"
    _src_untouched(setup)


def test_draft_and_rejected_fail_closed(setup):
    drafted = propose_skill(
        setup["store"],
        what="Draft only",
        why="should not write",
        how="SOP",
        where="skills/draft-only/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="agent-builder",
        prefer_existing_agent_id="review",
    )
    with pytest.raises(ValueError, match="approved"):
        commit_skill_pack(
            setup["store"],
            proposal_id=drafted["proposal_id"],
            data_dir=setup["data_dir"],
            catalog=setup["catalog"],
        )
    parked = commit_skill_pack(
        setup["store"],
        proposal_id=drafted["proposal_id"],
        data_dir=setup["data_dir"],
        catalog=setup["catalog"],
        approval_mode="ask",
    )
    assert parked["disk_written"] is False
    assert parked.get("parked") is True
    assert not (setup["skills_dir"] / "draft-only" / "SKILL.md").exists()

    rejected = propose_workflow(
        setup["store"],
        what="Rejected SOP",
        why="no",
        how="steps",
        where="skills/rejected-sop/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="agent-builder",
        prefer_existing_agent_id="review",
    )
    apply_skill_proposal_decision(
        setup["store"],
        proposal_id=rejected["proposal_id"],
        decision="rejected",
    )
    with pytest.raises(ValueError, match="Rejected"):
        commit_skill_pack(
            setup["store"],
            proposal_id=rejected["proposal_id"],
            data_dir=setup["data_dir"],
            catalog=setup["catalog"],
        )
    assert not (setup["skills_dir"] / "rejected-sop" / "SKILL.md").exists()
    _src_untouched(setup)


def test_commit_tool_merges_json_stub_not_python(setup):
    created = propose_tool(
        setup["store"],
        what="List lab users",
        why="directory lookup",
        how="JSON stub merged into SKILL.md; not a Python builtin",
        where="skills/lab-dir/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="agent-builder",
        pack_id="lab-dir",
        tool_json={
            "name": "lab_list_users",
            "description": "Stub: list lab users.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            "handler": "src.application.skills.lab_skill.handler",
        },
        prefer_existing_agent_id="review",
    )
    _approve(setup, created)
    result = commit_skill_pack(
        setup["store"],
        proposal_id=created["proposal_id"],
        data_dir=setup["data_dir"],
        catalog=setup["catalog"],
    )
    assert result["disk_written"] is True
    assert result["src_written"] is False
    dest = setup["skills_dir"] / "lab-dir" / "SKILL.md"
    body = dest.read_text(encoding="utf-8")
    assert "lab_list_users" in body
    assert "src.application.skills" not in body
    opened = setup["catalog"].read_pack("lab-dir")
    names = [t["name"] for t in opened["tools"]]
    assert "lab_list_users" in names
    _src_untouched(setup)


def test_commit_surfaces_soft_sprawl_warning(setup):
    created = propose_tool(
        setup["store"],
        what="extra tool",
        why="need it",
        how="JSON stub",
        where="skills/sprawl-demo/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="agent-builder",
        pack_id="sprawl-demo",
        tool_json={"name": "extra_tool", "description": "stub", "parameters": {}},
        prefer_existing_agent_id="coding",
        agent_registry=setup["registry"],
    )
    assert created["sprawl_warning"]
    _approve(setup, created)
    result = commit_skill_pack(
        setup["store"],
        proposal_id=created["proposal_id"],
        data_dir=setup["data_dir"],
        catalog=setup["catalog"],
        agent_registry=setup["registry"],
    )
    assert result["disk_written"] is True
    assert result["sprawl_warning"]
    assert ">= 12" in result["sprawl_warning"]


@pytest.mark.asyncio
async def test_agent_builder_tool_commits_after_approve(setup):
    token = _tool_context.set({"agent_id": "agent-builder", "session_id": "sess_ab", "approval_mode": "run"})
    try:
        created = await setup["skill"].propose_skill(
            what="Studio-visible pack",
            why="Skills Studio should open the same file",
            how="SOP body",
            where="skills/studio-pack/SKILL.md",
            prefer_existing_agent_id="review",
        )
        apply_skill_proposal_decision(
            setup["store"],
            proposal_id=created["proposal_id"],
            decision="approved",
        )
        result = await setup["skill"].commit_skill_pack(proposal_id=created["proposal_id"])
    finally:
        _tool_context.reset(token)
    assert result["disk_written"] is True
    assert (setup["skills_dir"] / "studio-pack" / "SKILL.md").is_file()


@pytest.mark.asyncio
async def test_coding_cannot_execute_propose_skill(setup):
    registry = ScopedToolRegistry()
    setup["skill"].register_tools(registry)
    assert "propose_skill" not in CODING_PROFILE.allowed_tool_names
    result = await registry.execute(
        ToolCall(id="tc1", name="propose_skill", arguments={"what": "x", "why": "y", "how": "z", "where": "skills/x/SKILL.md"}),
        CODING_PROFILE,
        session_id="sess_code",
    )
    assert result.success is False
    assert "not authorized" in (result.error or "")
    assert setup["store"].get_pending_approvals(session_id="sess_code") == []
    builder_ok = "propose_skill" in AGENT_BUILDER_PROFILE.allowed_tool_names
    assert builder_ok
