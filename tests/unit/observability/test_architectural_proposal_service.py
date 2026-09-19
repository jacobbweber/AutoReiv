"""
Unit tests for CARD-365: Architectural Proposal Service Lifecycle & Remediation Execution.
[REQ-ARCH-010] Durable Ledger Storage.
[REQ-ARCH-011] One-Click Proposal Remediation Execution.
"""

import json
from unittest.mock import MagicMock

from src.application.observability.architectural_proposals import (
    ArchitecturalProposalService,
)
from src.domain.observability.models import (
    ArchitecturalAlert,
    ArchitecturalProposal,
    ArchitecturalProposalStatus,
    ArchitecturalProposalType,
    ArchitecturalThresholdType,
)


def test_service_generates_and_persists_proposals_to_ledger(tmp_path):
    """Verify that service saves generated proposals to $DATA_DIR/telemetry/architectural_proposals.json."""
    store = MagicMock()
    service = ArchitecturalProposalService(store=store, data_dir=tmp_path)

    alert = ArchitecturalAlert(
        id="alert-life-1",
        threshold_type=ArchitecturalThresholdType.LIFECYCLE_MISMATCH,
        severity="high",
        agent_id="sre-agent",
        session_id="sess-1",
        evidence="Session exhibited 8 consecutive unattended polling turns.",
        remediation_proposal="Extract recurring unattended loops into scheduled Routines.",
        metadata={"automated_turns": 8},
    )

    created = service.generate_from_alerts([alert])
    assert len(created) == 1
    assert created[0].proposal_type == ArchitecturalProposalType.PROMOTION_ROUTINE

    # Check file on disk
    ledger_path = tmp_path / "telemetry" / "architectural_proposals.json"
    assert ledger_path.exists()
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["id"] == created[0].id
    assert data[0]["status"] == "pending"


def test_service_list_proposals_filters_by_status_and_agent(tmp_path):
    """Verify filtering by status, agent_id, and proposal_type."""
    service = ArchitecturalProposalService(store=None, data_dir=tmp_path)

    p1 = ArchitecturalProposal(
        id="prop-1",
        alert_id="a-1",
        proposal_type=ArchitecturalProposalType.PROMOTION_ROUTINE,
        status=ArchitecturalProposalStatus.PENDING,
        title="P1",
        description="D1",
        agent_id="agent-a",
        impact_summary="I1",
        action_payload={},
    )
    p2 = ArchitecturalProposal(
        id="prop-2",
        alert_id="a-2",
        proposal_type=ArchitecturalProposalType.TOOL_PRUNING,
        status=ArchitecturalProposalStatus.APPLIED,
        title="P2",
        description="D2",
        agent_id="agent-b",
        impact_summary="I2",
        action_payload={},
    )
    p3 = ArchitecturalProposal(
        id="prop-3",
        alert_id="a-3",
        proposal_type=ArchitecturalProposalType.CONTRACT_REINFORCEMENT,
        status=ArchitecturalProposalStatus.PENDING,
        title="P3",
        description="D3",
        agent_id="agent-b",
        impact_summary="I3",
        action_payload={},
    )

    service._save_proposals([p1, p2, p3])

    # Pending proposals for agent-b
    pending_b = service.list_proposals(status="pending", agent_id="agent-b")
    assert len(pending_b) == 1
    assert pending_b[0].id == "prop-3"

    # All pending
    all_pending = service.list_proposals(status="pending")
    assert len(all_pending) == 2

    # All applied
    all_applied = service.list_proposals(status="applied")
    assert len(all_applied) == 1
    assert all_applied[0].id == "prop-2"


def test_service_apply_promotion_routine_creates_routine(tmp_path):
    """Verify that applying a PROMOTION_ROUTINE proposal registers a Routine in store."""
    mock_store = MagicMock()
    mock_store.save_routine = MagicMock()

    service = ArchitecturalProposalService(store=mock_store, data_dir=tmp_path)

    proposal = ArchitecturalProposal(
        id="prop-apply-1",
        alert_id="a-life",
        proposal_type=ArchitecturalProposalType.PROMOTION_ROUTINE,
        status=ArchitecturalProposalStatus.PENDING,
        title="Promote Chat Polling to Hourly Routine",
        description="D1",
        agent_id="sre-agent",
        impact_summary="I1",
        action_payload={
            "routine_name": "SRE Daemon Poller",
            "prompt_template": "Check health of services and report failures.",
            "schedule_type": "interval",
            "interval_seconds": 3600,
            "approval_mode": "ask",
        },
    )
    service._save_proposals([proposal])

    result = service.apply_proposal("prop-apply-1")
    assert result["success"] is True
    assert result["applied"] is True
    assert "routine_id" in result

    # Check that store.save_routine was invoked
    mock_store.save_routine.assert_called_once()
    saved_routine = mock_store.save_routine.call_args[0][0]
    assert saved_routine.name == "SRE Daemon Poller"
    assert saved_routine.agent_id == "sre-agent"
    assert saved_routine.interval_seconds == 3600

    # Verify proposal status in ledger transitioned to applied
    updated = service.get_proposal("prop-apply-1")
    assert updated is not None
    assert updated.status == ArchitecturalProposalStatus.APPLIED
    assert updated.applied_at is not None


def test_service_dismiss_proposal(tmp_path):
    """Verify dismissing an architectural proposal."""
    service = ArchitecturalProposalService(store=None, data_dir=tmp_path)

    proposal = ArchitecturalProposal(
        id="prop-dismiss-1",
        alert_id="a-dismiss",
        proposal_type=ArchitecturalProposalType.TOOL_PRUNING,
        status=ArchitecturalProposalStatus.PENDING,
        title="Prune Tools",
        description="D1",
        agent_id="dev-agent",
        impact_summary="I1",
        action_payload={"current_tool_count": 10},
    )
    service._save_proposals([proposal])

    result = service.dismiss_proposal("prop-dismiss-1")
    assert result["success"] is True
    assert result["dismissed"] is True

    updated = service.get_proposal("prop-dismiss-1")
    assert updated is not None
    assert updated.status == ArchitecturalProposalStatus.DISMISSED
    assert updated.dismissed_at is not None
