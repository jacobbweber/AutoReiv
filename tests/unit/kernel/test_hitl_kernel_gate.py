"""
Kernel HITL gate: park real mutating tools and deny dangerous cli_exec [REQ-HITL-010..014].
"""

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _kernel():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    registry = ScopedToolRegistry()
    executed = {"cli_exec": 0}

    def cli_exec(**kwargs):
        executed["cli_exec"] += 1
        return {"exit_code": 0, "stdout": "ran"}

    registry.register_tool(
        name="cli_exec",
        description="exec",
        parameters={"type": "object", "properties": {"command": {"type": "string"}}},
        handler=cli_exec,
    )
    kernel = AgentKernel(
        gateway=None,
        tool_registry=registry,
        state_store=store,
        telemetry=TelemetryCollector(store),
        hitl_engine=HITLApprovalEngine(store=store),
    )
    profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="sre",
        system_prompt="x",
        allowed_tool_names=["cli_exec"],
    )
    return kernel, store, executed, profile


def test_cli_exec_is_high_risk_by_default():
    engine = HITLApprovalEngine(store=SQLiteStateStore(db_path=":memory:"))
    assert engine.requires_approval(ToolCall(id="1", name="cli_exec", arguments={"command": "dir"}))
    assert not engine.requires_approval(ToolCall(id="2", name="system_info", arguments={}))


def test_gate_parks_cli_exec_without_running_it():
    kernel, store, executed, profile = _kernel()
    tc = ToolCall(id="c1", name="cli_exec", arguments={"command": "dir"})
    gated = kernel._gate_tool_call(tc, session_id="s1", agent=profile)
    assert gated is not None
    assert gated.success is False
    assert str(gated.error).startswith("approval_required:")
    assert executed["cli_exec"] == 0
    pending = store.get_pending_approvals(session_id="s1")
    assert len(pending) == 1
    assert pending[0]["tool_name"] == "cli_exec"


def test_gate_denies_dangerous_cli_without_parking():
    kernel, store, executed, profile = _kernel()
    tc = ToolCall(id="c2", name="cli_exec", arguments={"command": "rm -rf /"})
    gated = kernel._gate_tool_call(tc, session_id="s1", agent=profile)
    assert gated is not None
    assert gated.success is False
    assert "Prohibited" in (gated.error or "")
    assert executed["cli_exec"] == 0
    assert store.get_pending_approvals(session_id="s1") == []


def test_gate_skips_park_when_approval_mode_run():
    kernel, store, executed, profile = _kernel()
    tc = ToolCall(id="c1", name="cli_exec", arguments={"command": "dir"})
    gated = kernel._gate_tool_call(tc, session_id="s1", agent=profile, approval_mode="run")
    assert gated is None
    assert store.get_pending_approvals(session_id="s1") == []


def test_gate_still_denies_dangerous_cli_in_run_mode():
    kernel, store, executed, profile = _kernel()
    tc = ToolCall(id="c2", name="cli_exec", arguments={"command": "rm -rf /"})
    gated = kernel._gate_tool_call(tc, session_id="s1", agent=profile, approval_mode="run")
    assert gated is not None
    assert "Prohibited" in (gated.error or "")
    assert executed["cli_exec"] == 0

