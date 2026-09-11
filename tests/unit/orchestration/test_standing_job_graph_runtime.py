"""CARD-215 Standing Job-Graph Runtime [REQ-JOBGRAPH-001, 001a, 001b, 002, 003].

Strict TDD: these assert standing routing without goal_mode theatre.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.standing_job_graph import (
    StandingRoute,
    is_multi_step_outcome,
    route_standing_chat,
)
from src.domain.orchestration.models import HandoffPacket, JobStatus, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


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
def orchestrator(temp_db_path):
    return JobPhaseOrchestrator(SQLiteStateStore(db_path=temp_db_path))


def test_req_jobgraph_001a_standing_routing_multi_step_vs_short():
    """Standing routing is explicit: multi-step -> job graph; short -> ReAct [REQ-JOBGRAPH-001a]."""
    multi = (
        "First research the homelab inventory, then draft a rollout plan, "
        "finally verify health checks pass."
    )
    assert is_multi_step_outcome(multi) is True
    assert route_standing_chat(multi) == StandingRoute.MULTI_STEP_JOB_GRAPH

    short = "What time is it"
    assert is_multi_step_outcome(short) is False
    assert route_standing_chat(short) == StandingRoute.SHORT_REACT

    numbered = "1. Scan hosts\n2. Patch critical CVEs\n3. Re-run health probe"
    assert route_standing_chat(numbered) == StandingRoute.MULTI_STEP_JOB_GRAPH


def test_req_jobgraph_001a_no_replacement_mode_flag_in_router_signature():
    """Do not reintroduce mode theatre via a new request flag [REQ-JOBGRAPH-001a]."""
    from src.web.routers.chat import ChatStreamRequest

    fields = set(ChatStreamRequest.model_fields.keys())
    # Legacy goal_mode may remain deprecated; no NEW standing/mode flag.
    for banned in (
        "standing_mode",
        "job_graph_mode",
        "plan_mode",
        "multi_step_mode",
        "use_job_graph",
        "auto_plan",
    ):
        assert banned not in fields


def test_req_jobgraph_orchestrator_replan_replaces_queued_phases(orchestrator):
    """formulate/advance/replan: replan replaces only queued remaining phases."""
    job = orchestrator.create_job_with_phases(
        goal="ship feature",
        session_id="sess_replan",
        agent_id="assistant",
        phase_specs=[
            {"name": "Research", "success_rule": "notes gathered"},
            {"name": "Build", "success_rule": "code landed"},
            {"name": "Verify", "success_rule": "tests green"},
        ],
    )
    phases = orchestrator._store.list_phases_for_job(job.id)
    first = orchestrator.start_phase(phases[0].id)
    orchestrator.complete_phase(
        first.id,
        HandoffPacket(goal="ship", facts=["notes"], constraints=[], done_when="ok", budget={}),
    )

    updated = orchestrator.replan_job(
        job.id,
        phase_specs=[
            {"name": "Rebuild", "success_rule": "new build"},
            {"name": "Retest", "success_rule": "retest pass"},
        ],
    )
    phases_after = orchestrator._store.list_phases_for_job(updated.id)
    done = [p for p in phases_after if p.status == PhaseStatus.DONE]
    queued = [p for p in phases_after if p.status == PhaseStatus.QUEUED]
    assert len(done) == 1
    assert done[0].name == "Research"
    assert [p.name for p in queued] == ["Rebuild", "Retest"]
    assert updated.current_phase_id == queued[0].id
    assert updated.status == JobStatus.RUNNING
