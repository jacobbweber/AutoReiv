"""
Unit tests for CARD-365: Architectural Proposal Domain Models.
[REQ-ARCH-008] Architectural Proposal Domain Model & Lifecycle.
"""

from datetime import datetime, timezone

from src.domain.observability.models import (
    ArchitecturalProposal,
    ArchitecturalProposalStatus,
    ArchitecturalProposalType,
)


def _utc_now():
    return datetime.now(timezone.utc)


def test_architectural_proposal_enums():
    """Verify proposal types and status enums exist per ADR-0054 and REQ-ARCH-008."""
    assert ArchitecturalProposalType.PROMOTION_ROUTINE == "promotion_routine"
    assert ArchitecturalProposalType.SKILL_DECOMPOSITION == "skill_decomposition"
    assert ArchitecturalProposalType.TOOL_PRUNING == "tool_pruning"
    assert ArchitecturalProposalType.SECURITY_ISOLATION == "security_isolation"
    assert ArchitecturalProposalType.CONTRACT_REINFORCEMENT == "contract_reinforcement"

    assert ArchitecturalProposalStatus.PENDING == "pending"
    assert ArchitecturalProposalStatus.APPLIED == "applied"
    assert ArchitecturalProposalStatus.DISMISSED == "dismissed"


def test_architectural_proposal_model_instantiation():
    """Verify ArchitecturalProposal creation, default fields, and serialization."""
    proposal = ArchitecturalProposal(
        id="prop-123",
        alert_id="alert-456",
        proposal_type=ArchitecturalProposalType.PROMOTION_ROUTINE,
        title="Promote Chat Polling to Hourly Routine",
        description="Session exhibited 8 consecutive unattended polling turns.",
        agent_id="sre-agent",
        session_id="sess-789",
        impact_summary="Frees interactive chat context and guarantees background cron execution.",
        action_payload={
            "routine_name": "SRE Background Poller",
            "prompt_template": "Check cluster health and alert on errors.",
            "interval_seconds": 3600,
            "approval_mode": "ask",
        },
    )

    assert proposal.id == "prop-123"
    assert proposal.status == ArchitecturalProposalStatus.PENDING
    assert proposal.applied_at is None
    assert proposal.dismissed_at is None
    assert isinstance(proposal.created_at, datetime)
    assert proposal.action_payload["routine_name"] == "SRE Background Poller"

    data = proposal.model_dump(mode="json")
    assert data["proposal_type"] == "promotion_routine"
    assert data["status"] == "pending"
    assert data["action_payload"]["interval_seconds"] == 3600
