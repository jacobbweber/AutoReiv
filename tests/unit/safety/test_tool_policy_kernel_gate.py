"""Kernel _gate_tool_call uses ToolPolicyGate [CARD-221]."""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.safety.tool_policy_gate import ToolPolicyGate
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall, ToolDefinition
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    s = SQLiteStateStore(db_path=path)
    yield s
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


def _kernel(store):
    reg = MagicMock()
    reg.list_tools.return_value = [
        ToolDefinition(name="wiki_note_search", description="search", parameters={}),
        ToolDefinition(name="cli_exec", description="shell", parameters={}),
    ]
    return AgentKernel(
        gateway=MagicMock(),
        tool_registry=reg,
        state_store=store,
        telemetry=TelemetryCollector(store),
        hitl_engine=HITLApprovalEngine(store=store),
        tool_policy_gate=ToolPolicyGate(store=store),
    )


def test_kernel_gate_listed_but_blocked_never_runs(store):
    store.set_setting("tool_policy", {"block_tools": ["wiki_note_search"], "require_confirm_tools": [], "safe_tools": []})
    k = _kernel(store)
    k.tool_policy_gate.reload_policy()
    agent = SimpleNamespace(
        id="assistant",
        allowed_tool_names=["wiki_note_search", "cli_exec"],
        storage_enabled=False,
        mcp_servers=[],
    )
    res = k._gate_tool_call(
        ToolCall(id="t1", name="wiki_note_search", arguments={}),
        "sess_k",
        agent,
        approval_mode="ask",
    )
    assert res is not None
    assert res.success is False
    assert "tool_policy_blocked" in str(res.error)


def test_kernel_gate_dangerous_parks(store):
    k = _kernel(store)
    agent = SimpleNamespace(
        id="assistant",
        allowed_tool_names=["cli_exec"],
        storage_enabled=False,
        mcp_servers=[],
    )
    res = k._gate_tool_call(
        ToolCall(id="t2", name="cli_exec", arguments={"command": "echo hi"}),
        "sess_k2",
        agent,
        approval_mode="ask",
    )
    assert res is not None
    assert str(res.error).startswith("approval_required:")
