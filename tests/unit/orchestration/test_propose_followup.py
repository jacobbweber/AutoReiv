"""
propose_followup draft job tests [REQ-ORCH-043].
"""

import json

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry, _tool_context
from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.orchestration.followup import apply_followup_decision, propose_followup_job
from src.application.orchestration.handoff_engine import HandoffIsolationEngine
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.skills.orchestration_skill import OrchestrationSkill
from src.domain.orchestration.models import (
    FOLLOWUP_JOB_TEMPLATE_ID,
    JobStatus,
    ProposalKind,
    ProposalStatus,
)
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def setup(tmp_path):
    store = SQLiteStateStore(db_path=tmp_path / "test_state.db")
    orch = JobPhaseOrchestrator(store)
    registry = BuiltinAgentRegistry(state_store=store)
    directory = AgentDirectoryService(agent_registry=registry, state_store=store)

    class MockStreamKernel:
        def __init__(self):
            self.stream_calls = []

        async def stream_turn(self, agent, session_id, user_content=None, approval_mode="ask", resume=False):
            self.stream_calls.append(
                {"agent": agent, "session_id": session_id, "user_content": user_content}
            )
            if False:
                yield None

    mock_kernel = MockStreamKernel()
    engine = HandoffIsolationEngine(
        agent_registry=registry,
        state_store=store,
        kernel_factory=lambda profile: mock_kernel,
    )
    skill = OrchestrationSkill(
        directory_service=directory,
        handoff_engine=engine,
        caller_agent_id="assistant",
        session_id="sess_root",
        store=store,
        orchestrator=orch,
    )
    parent = orch.create_single_phase_job(
        goal="Parent work",
        session_id="sess_root",
        agent_id="assistant",
        name="Chat",
    )
    return {
        "store": store,
        "orch": orch,
        "skill": skill,
        "mock_kernel": mock_kernel,
        "parent": parent,
    }


def test_orchestration_skill_schema_includes_propose_followup(setup):
    registry = ScopedToolRegistry()
    setup["skill"].register_tools(registry)
    names = [item.name for item in registry.list_tools()]
    assert "propose_followup" in names
    assert "handoff_to_agent" in names
    assert "set_goal" not in names
    definition = registry.get_tool_definition("propose_followup")
    assert definition is not None
    props = definition.parameters["properties"]
    assert "goal" in props
    assert "facts" in props
    assert "constraints" in props
    assert "parent_job_id" in props
    assert "goal" in definition.parameters["required"]


def test_propose_creates_queued_job_without_stream_turn(setup):
    mock_kernel = setup["mock_kernel"]
    store = setup["store"]
    parent = setup["parent"]
    result = propose_followup_job(
        store,
        setup["orch"],
        goal="Investigate the extra finding",
        session_id="sess_root",
        agent_id="assistant",
        parent_job_id=parent.id,
        facts=["disk is 90% full"],
        constraints=["do not reboot"],
    )
    assert mock_kernel.stream_calls == []
    assert result["status"] == "draft"
    assert result["job_status"] == "queued"
    assert result["auto_run"] is False
    assert result["parent_job_id"] == parent.id

    proposal = store.get_proposal(result["proposal_id"])
    assert proposal.kind == ProposalKind.FOLLOWUP_JOB
    assert proposal.status == ProposalStatus.DRAFT
    assert proposal.requested_by_job_id == parent.id
    payload = json.loads(proposal.payload_json)
    assert payload["goal"] == "Investigate the extra finding"
    assert payload["facts"] == ["disk is 90% full"]
    assert payload["constraints"] == ["do not reboot"]
    assert payload["requested_by_agent_id"] == "assistant"
    assert payload["requested_by_session_id"] == "sess_root"
    assert payload["job_id"] == result["job_id"]

    job = store.get_job(result["job_id"])
    assert job.status == JobStatus.QUEUED
    assert job.template_id == FOLLOWUP_JOB_TEMPLATE_ID
    phases = store.list_phases_for_job(job.id)
    assert len(phases) == 1
    assert phases[0].status.value == "queued"
    assert phases[0].react_state is None

    pending = store.get_pending_approvals(session_id="sess_root")
    assert any(row["id"] == result["approval_id"] for row in pending)
    assert any(row["tool_name"] == "propose_followup" for row in pending)


def test_propose_followup_tool_does_not_call_kernel(setup):
    token = _tool_context.set(
        {"agent_id": "assistant", "session_id": "sess_root", "job_id": setup["parent"].id}
    )
    try:
        text = setup["skill"].propose_followup(
            goal="Draft a follow-up from mid-flight",
            facts=["found extra table"],
        )
    finally:
        _tool_context.reset(token)
    assert "draft" in text.lower() or "not started" in text.lower()
    assert "job_id:" in text
    assert setup["mock_kernel"].stream_calls == []
    assert "set_goal" in text.lower() or "Auto-run: no" in text


def test_reject_does_not_start(setup):
    store = setup["store"]
    orch = setup["orch"]
    parent = setup["parent"]
    created = propose_followup_job(
        store,
        orch,
        goal="Do not run this",
        session_id="sess_root",
        agent_id="assistant",
        parent_job_id=parent.id,
    )
    decided = apply_followup_decision(
        store,
        orch,
        proposal_id=created["proposal_id"],
        job_id=created["job_id"],
        decision="rejected",
    )
    assert decided["started"] is False
    assert decided["status"] == "rejected"
    proposal = store.get_proposal(created["proposal_id"])
    assert proposal.status == ProposalStatus.REJECTED
    job = store.get_job(created["job_id"])
    assert job.status == JobStatus.CANCELLED
    assert setup["mock_kernel"].stream_calls == []


def test_approve_unblocks_queued_job_without_stream_turn(setup):
    store = setup["store"]
    orch = setup["orch"]
    parent = setup["parent"]
    created = propose_followup_job(
        store,
        orch,
        goal="Stay queued after accept",
        session_id="sess_root",
        agent_id="assistant",
        parent_job_id=parent.id,
    )
    decided = apply_followup_decision(
        store,
        orch,
        proposal_id=created["proposal_id"],
        job_id=created["job_id"],
        decision="approved",
    )
    assert decided["started"] is False
    assert decided["status"] == "approved"
    proposal = store.get_proposal(created["proposal_id"])
    assert proposal.status == ProposalStatus.APPROVED
    job = store.get_job(created["job_id"])
    assert job.status == JobStatus.QUEUED
    phases = store.list_phases_for_job(job.id)
    assert phases[0].status.value == "queued"
    assert setup["mock_kernel"].stream_calls == []


def test_latest_open_job_skips_followup_template(setup):
    from src.application.orchestration.chat_job_binding import latest_open_job_for_session

    store = setup["store"]
    parent = setup["parent"]
    propose_followup_job(
        store,
        setup["orch"],
        goal="Must not steal session resume",
        session_id="sess_root",
        agent_id="assistant",
        parent_job_id=parent.id,
    )
    opened = latest_open_job_for_session(store, "sess_root")
    assert opened is not None
    assert opened.id == parent.id
    assert opened.template_id != FOLLOWUP_JOB_TEMPLATE_ID
