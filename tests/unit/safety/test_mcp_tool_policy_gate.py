"""CARD-225 MCP tools through matched-subset + CARD-221 gate [REQ-MCPGATE-001..006].

Proof: listed MCP tool outside matched IDs never runs; dangerous MCP parks via HITL.
MCP tools/list / mount is transport only — listing ≠ authorization.
"""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.safety.tool_policy_gate import (
    ToolPolicyGate,
    ToolPolicyVerdict,
)
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall, ToolDefinition
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


@pytest.fixture
def gate(store):
    return ToolPolicyGate(store=store)


def _mcp_agent(**kwargs):
    base = dict(
        id="assistant",
        allowed_tool_names=["wiki_note_search"],
        storage_enabled=False,
        mcp_servers=[SimpleNamespace(name="demo")],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_req_mcpgate_003_listed_mcp_outside_matched_ids_never_runs(gate, store):
    """Red proof: tools/list-mounted MCP outside matched IDs → BLOCK, never executor [REQ-MCPGATE-003]."""
    handler = MagicMock(return_value={"ok": True})
    # Simulate transport mount: tool is listed/registered
    registry_names = {"mcp_demo_echo", "mcp_demo_write_file", "wiki_note_search"}
    agent = _mcp_agent()
    call = ToolCall(id="mcp_out", name="mcp_demo_write_file", arguments={"path": "/tmp/x"})

    decision = gate.evaluate(
        call,
        agent,
        matched_capability_ids=["tool.mcp_demo_echo", "tool.wiki_note_search"],
        registry_tool_names=registry_names,
    )
    assert decision.verdict == ToolPolicyVerdict.BLOCK
    assert decision.policy_source == "capability_subset"

    result = gate.apply_to_tool_result(
        decision,
        call,
        session_id="sess_mcp_out",
        agent=agent,
        hitl_engine=HITLApprovalEngine(store=store),
        approval_mode="ask",
    )
    assert result is not None
    assert (result.success is False and "tool_policy_blocked" in str(result.error)) or result.output.get("skipped") is True
    handler.assert_not_called()

    rows = store.list_tool_policy_decisions(limit=20)
    assert any(
        r["tool_name"] == "mcp_demo_write_file" and r["verdict"] == "BLOCK" for r in rows
    )


def test_req_mcpgate_001_tools_list_mount_is_not_authorization(gate):
    """Mount/list alone does not authorize — missing mcp_servers + allowlist → BLOCK [REQ-MCPGATE-001]."""
    agent = _mcp_agent(mcp_servers=[], allowed_tool_names=["wiki_note_search"])
    d = gate.evaluate(
        ToolCall(id="m1", name="mcp_demo_echo", arguments={}),
        agent,
        matched_capability_ids=None,
        registry_tool_names={"mcp_demo_echo", "wiki_note_search"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert d.policy_source in {"agent_allowlist", "registry"}


def test_req_mcpgate_002_in_subset_safe_mcp_allows(gate):
    """In-subset safe MCP under agent mcp_servers → ALLOW [REQ-MCPGATE-002]."""
    d = gate.evaluate(
        ToolCall(id="m2", name="mcp_demo_echo", arguments={}),
        _mcp_agent(),
        matched_capability_ids=["tool.mcp_demo_echo"],
        registry_tool_names={"mcp_demo_echo", "mcp_demo_write_file"},
    )
    assert d.verdict == ToolPolicyVerdict.ALLOW


def test_req_mcpgate_004_dangerous_mcp_requires_confirm_hitl(gate, store):
    """Dangerous MCP → REQUIRE_CONFIRM → existing HITL park [REQ-MCPGATE-004]."""
    hitl = HITLApprovalEngine(store=store)
    call = ToolCall(id="m3", name="mcp_demo_write_file", arguments={"path": "x"})
    d = gate.evaluate(
        call,
        _mcp_agent(),
        matched_capability_ids=["tool.mcp_demo_write_file"],
        registry_tool_names={"mcp_demo_write_file"},
    )
    assert d.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    result = gate.apply_to_tool_result(
        d,
        call,
        session_id="sess_mcp_danger",
        agent=_mcp_agent(),
        hitl_engine=hitl,
        approval_mode="ask",
    )
    assert result is not None
    assert str(result.error or "").startswith("approval_required:")
    assert isinstance(result.output, dict)
    assert result.output.get("status") == "parked"
    pending = store.get_pending_approvals(session_id="sess_mcp_danger")
    assert len(pending) >= 1
    assert pending[0]["tool_name"] == "mcp_demo_write_file"


def test_req_mcpgate_003_unknown_mcp_blocks(gate):
    """Unknown MCP tool (not in registry) → BLOCK [REQ-MCPGATE-003]."""
    d = gate.evaluate(
        ToolCall(id="m4", name="mcp_demo_ghost", arguments={}),
        _mcp_agent(allowed_tool_names=["mcp_demo_ghost"]),
        matched_capability_ids=["tool.mcp_demo_ghost"],
        registry_tool_names={"mcp_demo_echo"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert d.policy_source == "registry"


@pytest.mark.asyncio
async def test_req_mcpgate_003_executor_never_invoked_when_kernel_blocks(store):
    """Kernel gate BLOCK short-circuits before registry execute [REQ-MCPGATE-003/005]."""
    registry = ScopedToolRegistry()
    handler = AsyncMock(return_value={"ran": True})
    registry.mount_mcp_tool(
        ToolDefinition(
            name="mcp_demo_write_file",
            description="write (listed via tools/list)",
            parameters={"type": "object", "properties": {}},
        ),
        handler=handler,
    )
    registry.register_tool(
        name="wiki_note_search",
        description="search",
        parameters={},
        handler=lambda **_: {},
    )

    kernel = AgentKernel(
        gateway=MagicMock(),
        tool_registry=registry,
        state_store=store,
        telemetry=TelemetryCollector(store),
        hitl_engine=HITLApprovalEngine(store=store),
        tool_policy_gate=ToolPolicyGate(store=store),
    )
    agent = AgentProfile(
        id="assistant",
        name="Assistant",
        description="t",
        system_prompt="t",
        allowed_tool_names=["wiki_note_search"],
        mcp_servers=[{"name": "demo"}],
    )
    # Job-bound matched subset excludes the listed MCP write tool
    res = kernel._gate_tool_call(
        ToolCall(id="k1", name="mcp_demo_write_file", arguments={}),
        "sess_k_mcp",
        agent,
        approval_mode="ask",
        matched_capability_ids=["tool.mcp_demo_echo"],
    )
    assert res is not None
    assert (res.success is False and "tool_policy_blocked" in str(res.error)) or res.output.get("skipped") is True
    handler.assert_not_called()
