"""
Unit tests for Architectural Proposals REST API [CARD-365 / REQ-ARCH-012].
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.domain.observability.models import (
    ArchitecturalProposal,
    ArchitecturalProposalStatus,
    ArchitecturalProposalType,
)
from src.web.app import create_app


def test_rest_api_proposals_listing():
    """[REQ-ARCH-012] Test GET /api/observability/architectural/proposals returns list."""
    app = create_app()
    client = TestClient(app)

    mock_proposals = [
        ArchitecturalProposal(
            id="prop-test-1",
            alert_id="alert-1",
            proposal_type=ArchitecturalProposalType.PROMOTION_ROUTINE,
            status=ArchitecturalProposalStatus.PENDING,
            title="Promote Polling to Routine",
            description="Test desc",
            agent_id="sre-agent",
            impact_summary="Frees tokens",
            action_payload={"interval_seconds": 3600},
        )
    ]

    with patch(
        "src.application.observability.architectural_proposals.ArchitecturalProposalService.list_proposals",
        return_value=mock_proposals,
    ):
        response = client.get("/api/observability/architectural/proposals?status=pending&agent_id=sre-agent")
        assert response.status_code == 200
        data = response.json()
        assert "proposals" in data
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["id"] == "prop-test-1"
        assert data["proposals"][0]["proposal_type"] == "promotion_routine"


def test_rest_api_proposals_generate():
    """[REQ-ARCH-012] Test POST /api/observability/architectural/proposals/generate triggers synthesis."""
    app = create_app()
    client = TestClient(app)

    mock_generated = [
        ArchitecturalProposal(
            id="prop-gen-1",
            alert_id="alert-2",
            proposal_type=ArchitecturalProposalType.CONTRACT_REINFORCEMENT,
            status=ArchitecturalProposalStatus.PENDING,
            title="Enforce Verification Contract",
            description="Test desc",
            agent_id="dev-agent",
            impact_summary="Test impact",
            action_payload={"verification_command": "pytest"},
        )
    ]

    with patch(
        "src.application.observability.architectural_proposals.ArchitecturalProposalService.generate_from_alerts",
        return_value=mock_generated,
    ):
        response = client.post("/api/observability/architectural/proposals/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["generated_count"] == 1
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["id"] == "prop-gen-1"


def test_rest_api_proposals_apply():
    """[REQ-ARCH-012] Test POST /api/observability/architectural/proposals/{proposal_id}/apply executes remedy."""
    app = create_app()
    client = TestClient(app)

    mock_result = {
        "success": True,
        "applied": True,
        "routine_id": "routine-sre-12345",
        "routine_name": "SRE Poller",
    }

    with patch(
        "src.application.observability.architectural_proposals.ArchitecturalProposalService.apply_proposal",
        return_value=mock_result,
    ):
        response = client.post("/api/observability/architectural/proposals/prop-test-1/apply")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["applied"] is True
        assert data["routine_id"] == "routine-sre-12345"


def test_rest_api_proposals_dismiss():
    """[REQ-ARCH-012] Test POST /api/observability/architectural/proposals/{proposal_id}/dismiss."""
    app = create_app()
    client = TestClient(app)

    mock_result = {
        "success": True,
        "dismissed": True,
        "proposal_id": "prop-test-1",
    }

    with patch(
        "src.application.observability.architectural_proposals.ArchitecturalProposalService.dismiss_proposal",
        return_value=mock_result,
    ):
        response = client.post("/api/observability/architectural/proposals/prop-test-1/dismiss")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["dismissed"] is True
        assert data["proposal_id"] == "prop-test-1"
