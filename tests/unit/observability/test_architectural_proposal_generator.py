"""
Unit tests for CARD-365: Autonomic Proposal Generation Engine.
[REQ-ARCH-009] Autonomic Proposal Generation Engine.
"""

from datetime import datetime, timezone

from src.application.observability.architectural_proposals import ArchitecturalProposalGenerator
from src.domain.observability.models import (
    ArchitecturalAlert,
    ArchitecturalProposal,
    ArchitecturalProposalStatus,
    ArchitecturalProposalType,
    ArchitecturalThresholdType,
)


def _utc_now():
    return datetime.now(timezone.utc)


def test_generator_synthesizes_routine_promotion_from_lifecycle_mismatch():
    """Verify LIFECYCLE_MISMATCH alerts produce PROMOTION_ROUTINE proposals."""
    alert = ArchitecturalAlert(
        id="alert-life-1",
        threshold_type=ArchitecturalThresholdType.LIFECYCLE_MISMATCH,
        severity="medium",
        agent_id="sre-agent",
        session_id="sess-life-1",
        evidence="Session exhibited 7 consecutive automated polling turns (avg 35.2s interval).",
        remediation_proposal="Extract recurring unattended loops into scheduled Routines.",
        metadata={"automated_turns": 7, "avg_interval_seconds": 35.2},
    )

    proposals = ArchitecturalProposalGenerator.generate_proposals([alert])
    assert len(proposals) == 1
    p = proposals[0]
    assert p.alert_id == alert.id
    assert p.proposal_type == ArchitecturalProposalType.PROMOTION_ROUTINE
    assert p.status == ArchitecturalProposalStatus.PENDING
    assert p.agent_id == "sre-agent"
    assert "Routine" in p.title
    assert "routine_name" in p.action_payload
    assert p.action_payload["schedule_type"] == "interval"
    assert p.action_payload["interval_seconds"] == 3600
    assert "tokens" in p.impact_summary.lower() or "context" in p.impact_summary.lower()


def test_generator_synthesizes_tool_pruning_from_tool_bloat():
    """Verify TOOL_BLOAT alerts produce TOOL_PRUNING proposals."""
    alert = ArchitecturalAlert(
        id="alert-bloat-1",
        threshold_type=ArchitecturalThresholdType.TOOL_BLOAT,
        severity="high",
        agent_id="dev-agent",
        session_id="sess-bloat-1",
        evidence="Turn mounted 12 tools (exceeding Rule of 7 threshold of 8).",
        remediation_proposal="Decompose capability into specialized child skills, or unbind unused tools.",
        metadata={"active_tool_count": 12, "max_active_tools": 8},
    )

    proposals = ArchitecturalProposalGenerator.generate_proposals([alert])
    assert len(proposals) == 1
    p = proposals[0]
    assert p.proposal_type == ArchitecturalProposalType.TOOL_PRUNING
    assert p.agent_id == "dev-agent"
    assert "Rule of 7" in p.title or "Tool" in p.title
    assert p.action_payload["current_tool_count"] == 12
    assert p.action_payload["target_tool_ceiling"] == 8


def test_generator_synthesizes_contract_reinforcement_from_cognitive_conflict():
    """Verify COGNITIVE_CONFLICT alerts produce CONTRACT_REINFORCEMENT proposals."""
    alert = ArchitecturalAlert(
        id="alert-cog-1",
        threshold_type=ArchitecturalThresholdType.COGNITIVE_CONFLICT,
        severity="high",
        agent_id="coder-agent",
        session_id="sess-cog-1",
        evidence="Session executed mutating tool 'write_project_file' with no deterministic test or verification call.",
        remediation_proposal="Enforce deterministic mechanical verification in runbook contracts.",
        metadata={"mutating_tools": ["write_project_file"], "verification_tools": []},
    )

    proposals = ArchitecturalProposalGenerator.generate_proposals([alert])
    assert len(proposals) == 1
    p = proposals[0]
    assert p.proposal_type == ArchitecturalProposalType.CONTRACT_REINFORCEMENT
    assert p.agent_id == "coder-agent"
    assert "Verification" in p.title
    assert "verification_command" in p.action_payload
    assert "pytest" in p.action_payload["verification_command"]


def test_generator_synthesizes_security_isolation_from_security_collision():
    """Verify SECURITY_COLLISION alerts produce SECURITY_ISOLATION proposals."""
    alert = ArchitecturalAlert(
        id="alert-sec-1",
        threshold_type=ArchitecturalThresholdType.SECURITY_COLLISION,
        severity="critical",
        agent_id="web-agent",
        session_id="sess-sec-1",
        evidence="Session co-mingled untrusted inputs ['web_search'] with mutating syscalls ['cli_exec'] without HITL gating.",
        remediation_proposal="Isolate untrusted ingress into a read-only sandboxed agent or stage human-in-the-loop approval gate.",
        metadata={"untrusted_tools": ["web_search"], "mutating_tools": ["cli_exec"]},
    )

    proposals = ArchitecturalProposalGenerator.generate_proposals([alert])
    assert len(proposals) == 1
    p = proposals[0]
    assert p.proposal_type == ArchitecturalProposalType.SECURITY_ISOLATION
    assert p.agent_id == "web-agent"
    assert "HITL" in p.title or "Security" in p.title
    assert "cli_exec" in p.action_payload.get("hitl_tools", [])


def test_generator_deduplicates_against_existing_proposals():
    """Verify that existing pending or applied proposals prevent duplicate generation."""
    alert = ArchitecturalAlert(
        id="alert-life-dup",
        threshold_type=ArchitecturalThresholdType.LIFECYCLE_MISMATCH,
        severity="medium",
        agent_id="sre-agent",
        session_id="sess-dup-1",
        evidence="Session exhibited 6 consecutive automated polling turns.",
        remediation_proposal="Extract recurring unattended loops into scheduled Routines.",
    )

    existing = [
        ArchitecturalProposal(
            id="prop-existing",
            alert_id="alert-life-dup",
            proposal_type=ArchitecturalProposalType.PROMOTION_ROUTINE,
            status=ArchitecturalProposalStatus.PENDING,
            title="Existing Proposal",
            description="Already staged",
            agent_id="sre-agent",
            impact_summary="Test",
            action_payload={},
        )
    ]

    proposals = ArchitecturalProposalGenerator.generate_proposals([alert], existing_proposals=existing)
    assert len(proposals) == 0
