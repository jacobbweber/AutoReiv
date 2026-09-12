"""CARD-227: Observability standing journey timeline correlated by job_id."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.observability.standing_journey import build_standing_journey
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.models import HandoffPacket
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def store(tmp_path: Path):
    s = SQLiteStateStore(db_path=str(tmp_path / "ctrl.db"))
    s.initialize_db()
    return s


def _seed_standing(store: SQLiteStateStore, tmp_path: Path):
    orch = JobPhaseOrchestrator(store, data_dir=tmp_path)
    # Minimal catalog stub so create_job_from_catalog_resolve works if needed.
    job = orch.create_job_with_phases(
        goal="CARD-227 standing journey proof",
        session_id="sess_sjurn",
        agent_id="assistant",
        phase_specs=[
            {"name": "Research", "success_rule": "notes"},
            {"name": "Execute", "success_rule": "ship"},
        ],
    )
    # Stamp matched catalog IDs via checkpoint path
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    store.save_job_phase_checkpoint(
        job_id=job.id,
        phase_id=phases[0].id,
        phase_index=0,
        verifier_status="skipped_no_checker",
        matched_capability_ids=["tool.wiki_note_search", "agent.assistant"],
    )
    orch.complete_phase(
        phases[0].id,
        HandoffPacket(
            goal="CARD-227",
            facts=["verify_status: skipped_no_checker"],
            constraints=[],
            done_when="notes",
            budget={},
        ),
    )
    orch.start_phase(phases[1].id)

    # Policy decisions with job_id (incl MCP BLOCK) [CARD-221/225/227]
    store.save_tool_policy_decision(
        {
            "id": "tpd_allow_wiki",
            "session_id": "sess_sjurn",
            "agent_id": "assistant",
            "job_id": job.id,
            "tool_name": "wiki_note_search",
            "verdict": "ALLOW",
            "reason": "matched subset safe",
            "policy_source": "capability_subset",
        }
    )
    store.save_tool_policy_decision(
        {
            "id": "tpd_mcp_block",
            "session_id": "sess_sjurn",
            "agent_id": "assistant",
            "job_id": job.id,
            "tool_name": "mcp_lab_rm_rf",
            "verdict": "BLOCK",
            "reason": "outside matched capability subset",
            "policy_source": "capability_subset",
        }
    )

    # Durable A2A child link (without full catalog resolve)
    child = orch.create_job_with_phases(
        goal=f"child of {job.id}",
        session_id="sess_sjurn",
        agent_id="assistant",
        phase_specs=[{"name": "Handoff", "success_rule": "done"}],
    )
    store.save_job_a2a_link(parent_job_id=job.id, child_job_id=child.id)

    # Kill/resume
    store2 = SQLiteStateStore(db_path=store.db_path)
    store2.initialize_db()
    orch2 = JobPhaseOrchestrator(store2, data_dir=tmp_path)
    resume = orch2.resume_after_crash(job.id)
    assert resume.resumed_from_checkpoint is True
    return job, store2, resume


def test_req_sjurn_001_002_build_standing_journey_by_job_id(store, tmp_path):
    """Filter one job_id → full standing path with required event kinds [REQ-SJURN-001/002]."""
    job, store2, resume = _seed_standing(store, tmp_path)
    journey = build_standing_journey(store2, job_id=job.id)

    assert journey["job_id"] == job.id
    assert journey["resumed_from_checkpoint"] is True
    kinds = {e["kind"] for e in journey["timeline"]}
    assert "job" in kinds or "job_created" in kinds
    assert "phase" in kinds
    assert "catalog_match" in kinds
    assert "verifier_status" in kinds
    assert "policy_decision" in kinds
    assert "a2a_child" in kinds
    assert "resumed_from_checkpoint" in kinds

    assert any(
        p.get("verdict") == "BLOCK" and str(p.get("tool_name", "")).startswith("mcp_")
        for p in journey["policy_decisions"]
    )
    assert resume.resumed_from_checkpoint is True
    assert journey["child_job_ids"], "expected durable A2A child_job_id"
    assert all(cid != job.id for cid in journey["child_job_ids"])


def test_req_sjurn_003_span_tree_correlation(store, tmp_path):
    """OTel-style GenAI agent span tree keyed by job_id [REQ-SJURN-003]."""
    job, store2, _ = _seed_standing(store, tmp_path)
    journey = build_standing_journey(store2, job_id=job.id)
    spans = journey["spans"]
    assert spans, "expected span tree"
    root = spans[0]
    assert root["trace_id"] == job.id or root.get("attributes", {}).get("job_id") == job.id
    assert "children" in root or any(s.get("parent_span_id") for s in spans)


def test_req_sjurn_004_api_and_ui_contract(store, tmp_path):
    """API + Observability UI filter job_id returns complete journey [REQ-SJURN-004/005]."""
    job, store2, _ = _seed_standing(store, tmp_path)
    app = create_app(state_store=store2)
    client = TestClient(app)
    res = client.get(f"/api/observability/standing-journey?job_id={job.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["job_id"] == job.id
    assert data["resumed_from_checkpoint"] is True
    assert data["timeline"]
    assert data["spans"]

    html = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    js = Path("src/web/static/modules/studios/observability.js").read_text(encoding="utf-8")
    assert "standingJourneyJobIdInput" in html
    assert "standingJourneyTimeline" in html
    assert "standing-journey" in js
    assert "loadStandingJourney" in js or "standingJourney" in js
