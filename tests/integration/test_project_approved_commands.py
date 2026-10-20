"""
Operator contract: per-project remembered cli_exec commands [CARD-733].
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def client_and_store(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_PROJECTS_DIR", str(tmp_path / "projects"))
    store = SQLiteStateStore(db_path=str(tmp_path / "card733.db"))
    store.initialize_db()
    app = create_app(state_store=store)
    with TestClient(app) as c:
        yield c, store, tmp_path


def test_approve_and_remember_cli_exec_allows_repeat_in_active_project_and_revokes(client_and_store):
    c, store, _ = client_and_store
    assert c.post("/api/projects", json={"slug": "alpha"}).status_code == 200
    assert c.post("/api/projects", json={"slug": "beta"}).status_code == 200
    assert c.put("/api/projects/selected", json={"slug": "alpha"}).status_code == 200

    # Initially no commands are remembered for alpha.
    initial = c.get("/api/projects/approved-commands")
    assert initial.status_code == 200
    assert initial.json() == {"success": True, "slug": "alpha", "commands": []}

    registry = c.app.state.registry
    agent = registry.get_profile("autoreiv")
    gate = ToolPolicyGate(store=store)
    tc_safe = ToolCall(id="call_1", name="cli_exec", arguments={"command": "python -c \"print('card733_ok')\""})

    # 1. First evaluation in balanced mode requires confirmation.
    first_decision = gate.evaluate(tc_safe, agent)
    assert first_decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM

    # Park the tool call and approve with remember_for_project=True via the real HITL endpoint.
    parked = gate.apply_to_tool_result(
        first_decision,
        tc_safe,
        session_id="sess_card733",
        agent=agent,
        hitl_engine=c.app.state.kernel.hitl_engine,
        approval_mode="ask",
    )
    assert parked is not None
    approval_id = parked.output["approval_id"]

    res = c.post(
        f"/api/approvals/{approval_id}/decision",
        json={"decision": "APPROVED", "session_id": "sess_card733", "remember_for_project": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "approved"
    assert body["remembered_for_project"] is True
    assert body["execution"]["ran"] is True

    # Durable setting now lists the exact normalized command for alpha.
    listed = c.get("/api/projects/approved-commands")
    assert listed.status_code == 200
    assert listed.json() == {
        "success": True,
        "slug": "alpha",
        "commands": ["python -c \"print('card733_ok')\""],
    }

    # 2. Second evaluation of the same command in project alpha is ALLOW without parking.
    second_decision = gate.evaluate(tc_safe, agent)
    assert second_decision.verdict == ToolPolicyVerdict.ALLOW
    assert second_decision.policy_source == "project_approved_command"
    assert (
        gate.apply_to_tool_result(
            second_decision,
            tc_safe,
            session_id="sess_card733",
            agent=agent,
            hitl_engine=c.app.state.kernel.hitl_engine,
            approval_mode="ask",
        )
        is None
    )

    # 3. Negative: a different command in the same project still requires confirmation.
    tc_other = ToolCall(id="call_2", name="cli_exec", arguments={"command": "python -c \"print('other')\""})
    other_decision = gate.evaluate(tc_other, agent)
    assert other_decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM

    # 4. Negative: switching to another project (beta) does not inherit alpha's remembered command.
    assert c.put("/api/projects/selected", json={"slug": "beta"}).status_code == 200
    assert c.get("/api/projects/approved-commands").json()["commands"] == []
    beta_decision = gate.evaluate(tc_safe, agent)
    assert beta_decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM

    # Switch back to alpha.
    assert c.put("/api/projects/selected", json={"slug": "alpha"}).status_code == 200
    assert gate.evaluate(tc_safe, agent).verdict == ToolPolicyVerdict.ALLOW

    # 5. Negative: strict approval mode still requires confirmation even for a remembered command.
    store.set_setting("approval_mode", "strict")
    strict_decision = gate.evaluate(tc_safe, agent)
    assert strict_decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    store.set_setting("approval_mode", "balanced")

    # 6. Negative: dangerous commands cannot be remembered and stay hard-blocked.
    svc = c.app.state.projects_service
    bad_add = svc.add_approved_command("rm -rf /", slug="alpha")
    assert bad_add["success"] is False
    tc_danger = ToolCall(id="call_danger", name="cli_exec", arguments={"command": "rm -rf /"})
    danger_decision = gate.evaluate(tc_danger, agent)
    assert danger_decision.verdict == ToolPolicyVerdict.BLOCK
    assert danger_decision.policy_source == "dangerous_command_filter"

    # 7. Revoking the command via DELETE /api/projects/approved-commands requires confirmation again.
    revoked = c.delete(
        "/api/projects/approved-commands",
        params={"command": "python -c \"print('card733_ok')\""},
    )
    assert revoked.status_code == 200
    assert revoked.json() == {"success": True, "slug": "alpha", "commands": []}
    after_revoke = gate.evaluate(tc_safe, agent)
    assert after_revoke.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
