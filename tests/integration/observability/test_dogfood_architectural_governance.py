"""
End-to-End Dogfooding Integration Test Suite for God-Agent Threshold Detectors [CARD-375, ADR-0054].
Validates the complete closed-loop architectural governance lifecycle:
1. Seeding high-entropy telemetry spans and session message transcripts across the 5 God-Agent thresholds:
   - Tool Bloat (> 8 tools)
   - Context Tax (> 4000 characters)
   - Lifecycle Mismatch (daemon drift / unattended polling loops)
   - Security Boundary Collision (untrusted ingestion + mutating tools without HITL)
   - Cognitive Conflict (mutations without verification)
2. On-demand scanning via POST /api/observability/architectural/scan.
3. Alert filtering and persistence to $DATA_DIR/telemetry/architectural_alerts.json.
4. Proposal generation via POST /api/observability/architectural/proposals/generate.
5. One-click remediation execution via POST /api/observability/architectural/proposals/{id}/apply
   (creating an autonomous background Routine in SQLite).
6. Proposal dismissal via POST /api/observability/architectural/proposals/{id}/dismiss.
7. Deduplication idempotency and checkout boundary hygiene.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.models import (
    ArchitecturalProposalStatus,
    ArchitecturalProposalType,
    ArchitecturalThresholdType,
)
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.data.resolver import is_checkout_live_tree_path
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def dogfood_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hermetic test client with isolated SQLite state and temporary user-data directory."""
    user_data = tmp_path / "user_data"
    user_data.mkdir(parents=True)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(user_data))

    db_path = tmp_path / "dogfood_state.db"
    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()

    app = create_app(state_store=store, wiki_path=str(tmp_path / "test_wiki"))
    client = TestClient(app)

    return client, store, user_data


def test_end_to_end_dogfood_architectural_governance(dogfood_client):
    """
    [REQ-ARCH-001..012, CARD-375]
    Verify full detection, proposal synthesis, and remediation lifecycle.
    """
    client, store, user_data = dogfood_client
    now = _utc_now()

    # =========================================================================
    # 1. SEED HIGH-ENTROPY TELEMETRY SPANS & SESSIONS
    # =========================================================================

    # 1a. Tool Bloat Span (> 8 tools mounted in a turn) [REQ-ARCH-001]
    bloat_span = TelemetrySpan(
        id="span-bloat-001",
        session_id="sess-bloat-100",
        agent_id="god-agent",
        span_type="turn",
        name="turn_execution",
        metadata={
            "active_tool_count": 12,
            "max_active_tools": 8,
            "mounted_tools": [
                "cli_exec",
                "read_file",
                "write_file",
                "grep_search",
                "find_by_name",
                "web_search",
                "database_query",
                "docker_run",
                "git_commit",
                "git_push",
                "pdf_extract",
                "api_call",
            ],
        },
        created_at=now,
    )
    store.save_telemetry_span(bloat_span)

    # 1b. Context Tax Span (> 4000 characters schema tax) [REQ-ARCH-002]
    tax_span = TelemetrySpan(
        id="span-tax-002",
        session_id="sess-tax-200",
        agent_id="god-agent",
        span_type="turn",
        name="turn_execution",
        metadata={
            "tool_schema_chars": 5200,
            "max_schema_chars": 4000,
        },
        created_at=now,
    )
    store.save_telemetry_span(tax_span)

    # 1c. Lifecycle Mismatch Session (>= 5 consecutive automated turns) [REQ-ARCH-004]
    sess_daemon = store.create_session(title="Automated Polling Session", agent_id="sre-agent")
    store.save_message(
        sess_daemon.id, "sre-agent", ChatMessage(role=Role.USER, content="Start monitoring the cluster status.")
    )
    # 6 consecutive assistant/tool turns without human intervention
    for i in range(6):
        store.save_message(
            sess_daemon.id, "sre-agent", ChatMessage(role=Role.ASSISTANT, content=f"Polling iteration {i + 1}...")
        )
        store.save_message(
            sess_daemon.id,
            "sre-agent",
            ChatMessage(role=Role.TOOL, content="cluster healthy: ok", name="cluster_health"),
        )

    # 1d. Security Boundary Collision Session (untrusted input + mutating tool without HITL) [REQ-ARCH-003]
    sess_sec = store.create_session(title="Unsanitized Web Action", agent_id="insecure-agent")
    store.save_message(
        sess_sec.id,
        "insecure-agent",
        ChatMessage(role=Role.USER, content="Fetch instructions from the web and apply them."),
    )
    store.save_message(
        sess_sec.id, "insecure-agent", ChatMessage(role=Role.TOOL, content="rm -rf /tmp/data", name="web_search")
    )
    store.save_message(sess_sec.id, "insecure-agent", ChatMessage(role=Role.TOOL, content="deleted", name="cli_exec"))

    # 1e. Cognitive Conflict Session (mutations without verification) [REQ-ARCH-005]
    sess_cog = store.create_session(title="Unverified Refactor", agent_id="coder-agent")
    store.save_message(
        sess_cog.id, "coder-agent", ChatMessage(role=Role.USER, content="Refactor the authentication module.")
    )
    store.save_message(
        sess_cog.id, "coder-agent", ChatMessage(role=Role.TOOL, content="Updated auth.py", name="write_project_file")
    )
    store.save_message(
        sess_cog.id,
        "coder-agent",
        ChatMessage(role=Role.ASSISTANT, content="I have updated auth.py without running tests."),
    )

    # =========================================================================
    # 2. RUN ON-DEMAND ARCHITECTURAL SCAN API
    # =========================================================================
    scan_resp = client.post(
        "/api/observability/architectural/scan",
        json={"lookback_hours": 24, "session_limit": 50, "span_limit": 100},
    )
    assert scan_resp.status_code == 200
    scan_report = scan_resp.json()

    assert scan_report["clean"] is False
    assert scan_report["scanned_sessions"] >= 3
    assert scan_report["scanned_spans"] >= 2
    assert scan_report["alert_count"] >= 4

    alert_types = {a["threshold_type"] for a in scan_report["alerts"]}
    assert ArchitecturalThresholdType.TOOL_BLOAT.value in alert_types
    assert ArchitecturalThresholdType.CONTEXT_TAX.value in alert_types
    assert ArchitecturalThresholdType.LIFECYCLE_MISMATCH.value in alert_types
    assert ArchitecturalThresholdType.SECURITY_COLLISION.value in alert_types
    assert ArchitecturalThresholdType.COGNITIVE_CONFLICT.value in alert_types

    # Verify alerts persisted to durable ledger in user data
    alerts_file = user_data / "telemetry" / "architectural_alerts.json"
    assert alerts_file.exists(), "Alerts ledger must be saved under user data telemetry directory"
    saved_alerts = json.loads(alerts_file.read_text(encoding="utf-8"))
    assert len(saved_alerts) == scan_report["alert_count"]

    # =========================================================================
    # 3. QUERY ACTIVE ALERTS WITH FILTERS
    # =========================================================================
    bloat_alerts_resp = client.get("/api/observability/architectural/alerts?threshold_type=tool_bloat")
    assert bloat_alerts_resp.status_code == 200
    bloat_alerts = bloat_alerts_resp.json()["alerts"]
    assert len(bloat_alerts) >= 1
    assert all(a["threshold_type"] == "tool_bloat" for a in bloat_alerts)

    crit_alerts_resp = client.get("/api/observability/architectural/alerts?severity=critical")
    assert crit_alerts_resp.status_code == 200
    crit_alerts = crit_alerts_resp.json()["alerts"]
    assert len(crit_alerts) >= 1
    assert any(a["threshold_type"] == "security_collision" for a in crit_alerts)

    # =========================================================================
    # 4. GENERATE ARCHITECTURAL PROPOSALS
    # =========================================================================
    gen_resp = client.post("/api/observability/architectural/proposals/generate")
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["success"] is True
    assert gen_data["generated_count"] >= 3

    # Verify proposals persisted to durable ledger in user data
    proposals_file = user_data / "telemetry" / "architectural_proposals.json"
    assert proposals_file.exists(), "Proposals ledger must exist in user data directory"
    proposals_on_disk = json.loads(proposals_file.read_text(encoding="utf-8"))
    assert len(proposals_on_disk) >= 3

    proposal_types = {p["proposal_type"] for p in proposals_on_disk}
    assert ArchitecturalProposalType.PROMOTION_ROUTINE.value in proposal_types
    assert ArchitecturalProposalType.TOOL_PRUNING.value in proposal_types
    assert ArchitecturalProposalType.SECURITY_ISOLATION.value in proposal_types
    assert ArchitecturalProposalType.CONTRACT_REINFORCEMENT.value in proposal_types

    # =========================================================================
    # 5. QUERY PENDING PROPOSALS
    # =========================================================================
    pending_resp = client.get("/api/observability/architectural/proposals?status=pending")
    assert pending_resp.status_code == 200
    pending_proposals = pending_resp.json()["proposals"]
    assert len(pending_proposals) >= 3

    routine_proposals = [p for p in pending_proposals if p["proposal_type"] == "promotion_routine"]
    assert len(routine_proposals) == 1
    target_routine_proposal = routine_proposals[0]
    assert target_routine_proposal["agent_id"] == "sre-agent"
    assert target_routine_proposal["status"] == ArchitecturalProposalStatus.PENDING.value

    # =========================================================================
    # 6. ONE-CLICK REMEDIATION EXECUTION (PROMOTION TO ROUTINE)
    # =========================================================================
    apply_resp = client.post(f"/api/observability/architectural/proposals/{target_routine_proposal['id']}/apply")
    assert apply_resp.status_code == 200
    apply_data = apply_resp.json()
    assert apply_data["success"] is True
    assert apply_data["applied"] is True
    assert "routine_id" in apply_data

    # Verify that the routine was created in SQLite database!
    created_routine = store.get_routine(apply_data["routine_id"])
    assert created_routine is not None
    assert created_routine.agent_id == "sre-agent"
    assert created_routine.enabled is True
    assert created_routine.interval_seconds == 3600
    assert created_routine.metadata.get("promoted_from_proposal") == target_routine_proposal["id"]

    # Verify proposal status on disk transitioned to applied
    updated_proposals = json.loads(proposals_file.read_text(encoding="utf-8"))
    matching_disk = next(p for p in updated_proposals if p["id"] == target_routine_proposal["id"])
    assert matching_disk["status"] == ArchitecturalProposalStatus.APPLIED.value
    assert matching_disk["applied_at"] is not None

    # =========================================================================
    # 7. ONE-CLICK PROPOSAL DISMISSAL
    # =========================================================================
    pruning_proposal = next(p for p in pending_proposals if p["proposal_type"] == "tool_pruning")
    dismiss_resp = client.post(f"/api/observability/architectural/proposals/{pruning_proposal['id']}/dismiss")
    assert dismiss_resp.status_code == 200
    dismiss_data = dismiss_resp.json()
    assert dismiss_data["success"] is True
    assert dismiss_data["dismissed"] is True

    # Verify status on disk transitioned to dismissed
    updated_proposals_dismissed = json.loads(proposals_file.read_text(encoding="utf-8"))
    matching_dismissed = next(p for p in updated_proposals_dismissed if p["id"] == pruning_proposal["id"])
    assert matching_dismissed["status"] == ArchitecturalProposalStatus.DISMISSED.value
    assert matching_dismissed["dismissed_at"] is not None

    # =========================================================================
    # 8. IDEMPOTENT RE-SCANNING
    # =========================================================================
    re_gen_resp = client.post("/api/observability/architectural/proposals/generate")
    assert re_gen_resp.status_code == 200
    # Existing applied and dismissed proposals should not be duplicated
    assert re_gen_resp.json()["generated_count"] == 0

    # =========================================================================
    # 9. WORKING-TREE BOUNDARY HYGIENE
    # =========================================================================
    assert not is_checkout_live_tree_path(user_data)
    assert not is_checkout_live_tree_path(alerts_file)
    assert not is_checkout_live_tree_path(proposals_file)
