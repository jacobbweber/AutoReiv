"""
propose_skill / propose_tool / propose_workflow HITL drafts [REQ-BUILD-001 - REQ-BUILD-008].
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.orchestration.skill_proposals import (
    ALLOWLIST_WARN_AT,
    PYTHON_BUILTIN_NOTE,
    apply_skill_proposal_decision,
    propose_skill,
    propose_tool,
    propose_workflow,
)
from src.application.skills.agent_builder_tools import AgentBuilderTools
from src.domain.orchestration.models import ProposalKind, ProposalStatus
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def setup(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "test_state.db")
    data_dir = tmp_path / "data"
    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True)
    canary = skills_dir / ".keep"
    canary.write_text("untouched\n", encoding="utf-8")
    registry = BuiltinAgentRegistry(state_store=store)
    skill = AgentBuilderTools(
        agent_registry=registry,
        tool_registry=ScopedToolRegistry(),
        store=store,
        data_dir=data_dir,
    )
    return {
        "store": store,
        "data_dir": data_dir,
        "skills_dir": skills_dir,
        "canary": canary,
        "registry": registry,
        "skill": skill,
        "src_skills": Path(__file__).resolve().parents[3] / "src" / "application" / "skills",
    }


def _snapshot_src(src_dir: Path) -> dict:
    if not src_dir.exists():
        return {}
    return {p.name: p.stat().st_mtime_ns for p in src_dir.glob("*.py")}


def _assert_disk_untouched(setup, src_before: dict) -> None:
    skills_dir: Path = setup["skills_dir"]
    names = {p.name for p in skills_dir.iterdir()}
    assert names == {".keep"}
    assert setup["canary"].read_text(encoding="utf-8") == "untouched\n"
    src_after = _snapshot_src(setup["src_skills"])
    assert src_after == src_before


def test_agent_builder_schema_includes_propose_tools(setup):
    registry = ScopedToolRegistry()
    setup["skill"].register_tools(registry)
    names = [item.name for item in registry.list_tools()]
    assert "propose_skill" in names
    assert "propose_tool" in names
    assert "propose_workflow" in names
    assert "list_available_skills_and_tools" in names
    assert "propose_agent_specification" in names
    assert "save_agent_specification" in names
    assert "commit_skill_pack" in names
    for tool_name in ("propose_skill", "propose_tool", "propose_workflow"):
        definition = registry.get_tool_definition(tool_name)
        assert definition is not None
        props = definition.parameters["properties"]
        required = definition.parameters["required"]
        for field in ("what", "why", "how", "where"):
            assert field in props
            assert field in required


def test_propose_skill_creates_draft_and_hitl_without_skill_md(setup):
    src_before = _snapshot_src(setup["src_skills"])
    result = propose_skill(
        setup["store"],
        what="Okta admin playbook for homelab directory ops",
        why="Operator resets / assigns in Okta without a live API skill yet",
        how="SKILL.md SOP plus JSON tool stubs; no Python builtin",
        where="skills/okta-admin/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        prefer_existing_agent_id="review",
    )
    assert result["status"] == "draft"
    assert result["kind"] == "skill"
    assert result["auto_run"] is False
    assert result["disk_written"] is False
    assert result["apply_on_approve"] is False
    assert result["where"] == "skills/okta-admin/SKILL.md"
    assert result["sprawl_warning"] is None

    proposal = setup["store"].get_proposal(result["proposal_id"])
    assert proposal.kind == ProposalKind.SKILL
    assert proposal.status == ProposalStatus.DRAFT
    payload = json.loads(proposal.payload_json)
    assert payload["what"].startswith("Okta admin")
    assert payload["why"]
    assert payload["how"]
    assert payload["where"] == "skills/okta-admin/SKILL.md"
    assert payload["kind"] == "skill"
    assert payload["target_pack_id"] == "okta-admin"

    pending = setup["store"].get_pending_approvals(session_id="sess_ab")
    assert any(row["id"] == result["approval_id"] for row in pending)
    assert any(row["tool_name"] == "propose_skill" for row in pending)
    _assert_disk_untouched(setup, src_before)


def test_propose_tool_creates_draft_without_python_file(setup):
    src_before = _snapshot_src(setup["src_skills"])
    result = propose_tool(
        setup["store"],
        what="List Okta users by login",
        why="Homelab directory lookup",
        how="JSON stub merged into SKILL.md; not a Python builtin",
        where="skills/okta-admin/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        pack_id="okta-admin",
        tool_json={
            "name": "okta_list_users",
            "description": "Stub: list Okta users.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
        prefer_existing_agent_id="review",
    )
    assert result["kind"] == "tool"
    assert result["status"] == "draft"
    proposal = setup["store"].get_proposal(result["proposal_id"])
    assert proposal.kind == ProposalKind.TOOL
    payload = json.loads(proposal.payload_json)
    assert payload["tool_json"]["name"] == "okta_list_users"
    assert not payload.get("python_builtin_note")
    jobs = []
    if hasattr(setup["store"], "list_jobs"):
        jobs = setup["store"].list_jobs()
    assert jobs == [] or all(getattr(j, "template_id", None) != "followup_job" for j in jobs)
    _assert_disk_untouched(setup, src_before)


def test_propose_workflow_is_playbook_not_job_yaml(setup):
    src_before = _snapshot_src(setup["src_skills"])
    result = propose_workflow(
        setup["store"],
        what="Unlock user SOP",
        why="Repeatable homelab unlock",
        how="Ordered playbook steps in SKILL.md body. Not job-template YAML.",
        where="skills/okta-admin/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        pack_id="okta-admin",
        prefer_existing_agent_id="review",
    )
    assert result["kind"] == "workflow"
    assert result["auto_run"] is False
    proposal = setup["store"].get_proposal(result["proposal_id"])
    assert proposal.kind == ProposalKind.WORKFLOW
    payload = json.loads(proposal.payload_json)
    assert "template_id" not in payload
    assert "yaml" not in payload["how"].lower() or "not job-template yaml" in payload["how"].lower()
    _assert_disk_untouched(setup, src_before)


def test_missing_field_fails_closed_no_row(setup):
    before = setup["store"].list_proposals_for_job("none") if False else None
    with pytest.raises(ValueError, match="why is required"):
        propose_skill(
            setup["store"],
            what="something",
            why="  ",
            how="steps",
            where="skills/x/SKILL.md",
            data_dir=setup["data_dir"],
            session_id="sess_ab",
            agent_id="assistant",
        )
    pending = setup["store"].get_pending_approvals(session_id="sess_ab")
    assert pending == []
    # no proposals table rows for this session
    # list via sqlite: create a dummy and ensure count of skill kinds is 0
    conn = setup["store"]._get_connection()
    try:
        rows = conn.execute("SELECT id FROM proposals").fetchall()
    finally:
        if setup["store"]._mem_conn is None:
            conn.close()
    assert rows == []
    assert before is None


def test_where_traversal_rejected(setup):
    with pytest.raises(ValueError, match="traversal|jailed"):
        propose_skill(
            setup["store"],
            what="evil",
            why="escape",
            how="write python",
            where="skills/../src/application/skills/evil.py",
            data_dir=setup["data_dir"],
            session_id="sess_ab",
            agent_id="assistant",
        )
    with pytest.raises(ValueError, match="jailed"):
        propose_skill(
            setup["store"],
            what="evil",
            why="escape",
            how="write python",
            where="src/application/skills/evil.py",
            data_dir=setup["data_dir"],
            session_id="sess_ab",
            agent_id="assistant",
        )
    conn = setup["store"]._get_connection()
    try:
        rows = conn.execute("SELECT id FROM proposals").fetchall()
    finally:
        if setup["store"]._mem_conn is None:
            conn.close()
    assert rows == []


@pytest.mark.asyncio
async def test_agent_builder_tool_parks_hitl(setup):
    token = _tool_context.set({"agent_id": "assistant", "session_id": "sess_ab"})
    try:
        result = await setup["skill"].propose_skill(
            what="Pack",
            why="Need it",
            how="SKILL.md SOP",
            where="skills/demo-pack/SKILL.md",
            prefer_existing_agent_id="review",
        )
    finally:
        _tool_context.reset(token)
    assert result["status"] == "draft"
    assert result["kind"] == "skill"
    assert "proposal_id" in result
    assert setup["store"].get_proposal(result["proposal_id"]).status == ProposalStatus.DRAFT


def test_approve_does_not_write_disk(setup):
    src_before = _snapshot_src(setup["src_skills"])
    created = propose_skill(
        setup["store"],
        what="Okta admin",
        why="homelab",
        how="SOP",
        where="skills/okta-admin/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        prefer_existing_agent_id="review",
    )
    decided = apply_skill_proposal_decision(
        setup["store"],
        proposal_id=created["proposal_id"],
        decision="approved",
    )
    assert decided["status"] == "approved"
    assert decided["disk_written"] is False
    assert decided["started"] is False
    proposal = setup["store"].get_proposal(created["proposal_id"])
    assert proposal.status == ProposalStatus.APPROVED
    _assert_disk_untouched(setup, src_before)

    again = apply_skill_proposal_decision(
        setup["store"],
        proposal_id=created["proposal_id"],
        decision="approved",
    )
    assert again["status"] == "approved"
    _assert_disk_untouched(setup, src_before)


def test_reject_does_not_write_disk(setup):
    src_before = _snapshot_src(setup["src_skills"])
    created = propose_workflow(
        setup["store"],
        what="SOP",
        why="ops",
        how="steps in SKILL.md",
        where="skills/okta-admin/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        prefer_existing_agent_id="review",
    )
    decided = apply_skill_proposal_decision(
        setup["store"],
        proposal_id=created["proposal_id"],
        decision="rejected",
    )
    assert decided["status"] == "rejected"
    assert decided["disk_written"] is False
    proposal = setup["store"].get_proposal(created["proposal_id"])
    assert proposal.status == ProposalStatus.REJECTED
    _assert_disk_untouched(setup, src_before)


def test_sprawl_warning_when_allowlist_would_be_12(setup):
    # Agent with 12 tools; adding a tool projects to 13.
    assert ALLOWLIST_WARN_AT == 12
    from src.domain.kernel.models import AgentProfile

    setup["registry"].register_custom_agent(
        AgentProfile(
            id="coding",
            name="Coding",
            description="Coding agent",
            system_prompt="Coding agent",
            allowed_tool_names=[f"tool_{i}" for i in range(12)],
        )
    )
    created = propose_tool(
        setup["store"],
        what="extra tool",
        why="need it",
        how="JSON stub",
        where="skills/demo/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        pack_id="demo",
        tool_json={"name": "extra_tool", "description": "stub", "parameters": {}},
        prefer_existing_agent_id="coding",
        agent_registry=setup["registry"],
    )
    assert created["status"] == "draft"
    assert created["sprawl_warning"]
    assert ">= 12" in created["sprawl_warning"]
    assert "coding" in created["sprawl_warning"]


def test_no_sprawl_warning_under_12(setup):
    created = propose_tool(
        setup["store"],
        what="small tool",
        why="need it",
        how="JSON stub",
        where="skills/demo/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        pack_id="demo",
        tool_json={"name": "small_tool", "description": "stub", "parameters": {}},
        prefer_existing_agent_id="review",
        agent_registry=setup["registry"],
    )
    assert created["sprawl_warning"] is None


def test_new_agent_sprawl_warning_does_not_block(setup):
    created = propose_skill(
        setup["store"],
        what="new specialist",
        why="maybe",
        how="SKILL.md",
        where="skills/demo/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        new_agent_id="okta-ops",
        agent_registry=setup["registry"],
    )
    assert created["status"] == "draft"
    assert created["sprawl_warning"]
    assert "okta-ops" in created["sprawl_warning"]
    assert "existing specialist" in created["sprawl_warning"].lower() or "Prefer adding" in created["sprawl_warning"]


def test_python_builtin_tool_stays_draft_with_note(setup):
    created = propose_tool(
        setup["store"],
        what="Python builtin",
        why="real handler",
        how="Python BuiltinSkill module under src/application/skills",
        where="skills/demo/SKILL.md",
        data_dir=setup["data_dir"],
        session_id="sess_ab",
        agent_id="assistant",
        pack_id="demo",
        tool_json={
            "name": "real_python_tool",
            "description": "would be a Python builtin",
            "handler": "src.application.skills.demo_skill.handler",
            "parameters": {},
        },
        prefer_existing_agent_id="review",
    )
    assert created["status"] == "draft"
    assert created["python_builtin_note"] == PYTHON_BUILTIN_NOTE
    payload = json.loads(setup["store"].get_proposal(created["proposal_id"]).payload_json)
    assert payload["python_builtin_note"] == PYTHON_BUILTIN_NOTE
    decided = apply_skill_proposal_decision(
        setup["store"],
        proposal_id=created["proposal_id"],
        decision="approved",
    )
    assert decided["disk_written"] is False
    assert not (setup["data_dir"] / "skills" / "demo" / "SKILL.md").exists()
