"""
Unit & Integration Tests for HITL Approval Manager [REQ-HITL-001 - REQ-HITL-004].
"""

import asyncio

import pytest
from starlette.testclient import TestClient

from src.application.hitl.approval_manager import ApprovalManager
from src.domain.hitl.models import ApprovalDecision, ApprovalStatus, PendingAction
from src.web.app import create_app


def test_hitl_domain_models():
    """Verify PendingAction and ApprovalDecision models [REQ-HITL-001]."""
    action = PendingAction(
        description="rm -rf /tmp/data",
        risk_level="high",
        agent_id="agent-1",
        session_id="session-1",
        tool_name="execute_code",
    )
    assert action.status == ApprovalStatus.PENDING
    assert action.action_id  # UUID auto-generated
    assert action.created_at > 0

    decision = ApprovalDecision(
        action_id=action.action_id,
        status=ApprovalStatus.APPROVED,
    )
    assert decision.status == ApprovalStatus.APPROVED
    assert decision.decided_at > 0


@pytest.mark.asyncio
async def test_park_action_returns_pending_action_and_future():
    """Verify park_action creates PendingAction + asyncio.Future [REQ-HITL-002]."""
    mgr = ApprovalManager()
    action, future = mgr.park_action(
        description="Delete production database",
        risk_level="critical",
        agent_id="agent-1",
        session_id="session-1",
        tool_name="execute_code",
        tool_args={"command": "drop database"},
    )

    assert isinstance(action, PendingAction)
    assert action.status == ApprovalStatus.PENDING
    assert isinstance(future, asyncio.Future)
    assert not future.done()
    assert len(mgr.list_pending()) == 1


@pytest.mark.asyncio
async def test_decide_approved_resolves_future():
    """Verify decide(APPROVED) resolves the parked future [REQ-HITL-002]."""
    mgr = ApprovalManager()
    action, future = mgr.park_action(
        description="Run migrations",
        risk_level="medium",
        agent_id="agent-2",
        session_id="session-2",
    )

    decision = mgr.decide(action.action_id, ApprovalStatus.APPROVED, reason="Looks safe")

    assert decision.status == ApprovalStatus.APPROVED
    assert decision.reason == "Looks safe"
    assert future.done()
    result = future.result()
    assert isinstance(result, ApprovalDecision)
    assert result.status == ApprovalStatus.APPROVED
    assert len(mgr.list_pending()) == 0


@pytest.mark.asyncio
async def test_decide_rejected_resolves_future():
    """Verify decide(REJECTED) resolves the parked future [REQ-HITL-002]."""
    mgr = ApprovalManager()
    action, future = mgr.park_action(
        description="Format disk",
        risk_level="critical",
        agent_id="agent-3",
        session_id="session-3",
    )

    decision = mgr.decide(action.action_id, ApprovalStatus.REJECTED, reason="Too dangerous")

    assert decision.status == ApprovalStatus.REJECTED
    assert future.done()
    result = future.result()
    assert result.status == ApprovalStatus.REJECTED
    assert len(mgr.list_pending()) == 0


def test_decide_unknown_action_raises_key_error():
    """Verify decide raises KeyError for unknown action_id [REQ-HITL-002]."""
    mgr = ApprovalManager()
    with pytest.raises(KeyError, match="No pending action"):
        mgr.decide("nonexistent-id", ApprovalStatus.APPROVED)


def test_hitl_rest_api_endpoints():
    """Verify GET /api/hitl/pending and POST /api/hitl/decide [REQ-HITL-003]."""
    app = create_app()
    client = TestClient(app)

    # Initially empty
    resp = client.get("/api/hitl/pending")
    assert resp.status_code == 200
    assert resp.json() == []

    # Park an action directly via the manager
    mgr = app.state.approval_manager
    action, _ = mgr.park_action(
        description="Test action",
        risk_level="high",
        agent_id="agent-test",
        session_id="session-test",
    )

    # Pending list should have one entry
    resp = client.get("/api/hitl/pending")
    assert resp.status_code == 200
    pending = resp.json()
    assert len(pending) == 1
    assert pending[0]["action_id"] == action.action_id

    # Approve the action via REST
    resp = client.post(
        "/api/hitl/decide",
        json={"action_id": action.action_id, "status": "approved", "reason": "Verified"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reason"] == "Verified"

    # Pending list should be empty again
    resp = client.get("/api/hitl/pending")
    assert resp.status_code == 200
    assert resp.json() == []

    # Deciding on a nonexistent action returns 404
    resp = client.post(
        "/api/hitl/decide",
        json={"action_id": "fake-id", "status": "rejected"},
    )
    assert resp.status_code == 404
