"""
Unit tests for HITL Approvals and High-Risk Tool Tagging [REQ-SAFE-003, REQ-SAFE-004].
"""

import pytest

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_sqlite_pending_approvals_crud(store):
    approval_id = store.create_approval(
        session_id="sess_abc",
        agent_id="sysadmin",
        tool_name="execute_command",
        arguments={"command": "systemctl restart nginx"},
    )
    assert approval_id is not None

    pending = store.get_pending_approvals(session_id="sess_abc")
    assert len(pending) == 1
    assert pending[0]["id"] == approval_id
    assert pending[0]["tool_name"] == "execute_command"
    assert pending[0]["status"] == "pending"

    # Resolve approval
    resolved = store.resolve_approval(approval_id, decision="approved", reason="Operator confirmed")
    assert resolved is True

    pending_after = store.get_pending_approvals(session_id="sess_abc")
    assert len(pending_after) == 0

    record = store.get_approval(approval_id)
    assert record["status"] == "approved"
    assert record["decision_reason"] == "Operator confirmed"


def test_hitl_engine_requires_approval_for_high_risk_tool(store):
    engine = HITLApprovalEngine(store=store, high_risk_tools=["execute_command", "drop_db"])

    safe_tc = ToolCall(id="c1", name="read_file", arguments={"path": "README.md"})
    high_risk_tc = ToolCall(id="c2", name="execute_command", arguments={"command": "reboot"})

    assert not engine.requires_approval(safe_tc)
    assert engine.requires_approval(high_risk_tc)

    # Park approval
    approval_id = engine.park_tool_call(
        session_id="sess_123",
        agent_id="sysadmin",
        tool_call=high_risk_tc,
    )
    assert approval_id is not None
