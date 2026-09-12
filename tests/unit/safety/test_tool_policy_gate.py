"""CARD-221 Tool Policy Gate [REQ-TOOLPOL-001..006].

TDD: listed-but-BLOCKED never runs; dangerous without approve stays parked.
"""

from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

import pytest

from src.application.kernel.hitl_engine import HITLApprovalEngine
from src.application.safety.tool_policy_gate import (
    ToolPolicyDecision,
    ToolPolicyGate,
    ToolPolicyVerdict,
)
from src.domain.gateway.models import ToolCall
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


def _agent(**kwargs):
    base = dict(
        id="assistant",
        allowed_tool_names=["wiki_note_search", "cli_exec", "wiki_note_create"],
        storage_enabled=False,
        mcp_servers=[],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_req_toolpol_001_verdict_enum_and_evaluate_returns_decision(gate):
    """Every call gets explicit ALLOW|REQUIRE_CONFIRM|BLOCK [REQ-TOOLPOL-001]."""
    d = gate.evaluate(
        ToolCall(id="c1", name="wiki_note_search", arguments={"q": "x"}),
        _agent(),
        registry_tool_names={"wiki_note_search", "cli_exec", "wiki_note_create"},
    )
    assert isinstance(d, ToolPolicyDecision)
    assert d.verdict in {
        ToolPolicyVerdict.ALLOW,
        ToolPolicyVerdict.REQUIRE_CONFIRM,
        ToolPolicyVerdict.BLOCK,
    }
    assert d.verdict == ToolPolicyVerdict.ALLOW


def test_req_toolpol_002_listed_but_blocked_never_runs(gate, store):
    """Registry listing ≠ authorization: explicit block prevents run [REQ-TOOLPOL-002]."""
    store.set_setting(
        "tool_policy",
        {
            "block_tools": ["wiki_note_search"],
            "require_confirm_tools": [],
            "safe_tools": [],
        },
    )
    # Refresh durable policy
    gate.reload_policy()
    d = gate.evaluate(
        ToolCall(id="c2", name="wiki_note_search", arguments={}),
        _agent(),
        registry_tool_names={"wiki_note_search", "cli_exec"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert "block" in d.reason.lower() or "blocked" in d.reason.lower()

    # Kernel-shaped apply: BLOCK => ToolResult failure, no park id execute
    result = gate.apply_to_tool_result(
        d,
        ToolCall(id="c2", name="wiki_note_search", arguments={}),
        session_id="sess_block",
        agent=_agent(),
        hitl_engine=HITLApprovalEngine(store=store),
        approval_mode="ask",
    )
    assert result is not None
    assert result.success is False
    assert not str(result.error or "").startswith("approval_required:")
    # Decision logged
    rows = store.list_tool_policy_decisions(limit=10)
    assert any(r["tool_name"] == "wiki_note_search" and r["verdict"] == "BLOCK" for r in rows)


def test_req_toolpol_003_dangerous_without_approve_stays_parked(gate, store):
    """Write/shell high-risk => REQUIRE_CONFIRM => HITL park [REQ-TOOLPOL-003]."""
    hitl = HITLApprovalEngine(store=store)
    d = gate.evaluate(
        ToolCall(id="c3", name="cli_exec", arguments={"command": "echo hi"}),
        _agent(),
        registry_tool_names={"cli_exec", "wiki_note_search"},
    )
    assert d.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    result = gate.apply_to_tool_result(
        d,
        ToolCall(id="c3", name="cli_exec", arguments={"command": "echo hi"}),
        session_id="sess_park",
        agent=_agent(),
        hitl_engine=hitl,
        approval_mode="ask",
    )
    assert result is not None
    assert result.success is False
    assert str(result.error or "").startswith("approval_required:")
    assert isinstance(result.output, dict)
    assert result.output.get("status") == "parked"
    pending = store.get_pending_approvals(session_id="sess_park")
    assert len(pending) >= 1
    assert pending[0]["tool_name"] == "cli_exec"
    assert pending[0]["status"] == "pending"


def test_req_toolpol_003_unknown_and_out_of_scope_block(gate):
    """Unknown / not allowlisted / not in matched subset => BLOCK [REQ-TOOLPOL-003]."""
    # Not in agent allowlist
    d1 = gate.evaluate(
        ToolCall(id="c4", name="secret_exfil", arguments={}),
        _agent(allowed_tool_names=["wiki_note_search"]),
        registry_tool_names={"secret_exfil", "wiki_note_search"},
    )
    assert d1.verdict == ToolPolicyVerdict.BLOCK

    # Unknown to registry
    d2 = gate.evaluate(
        ToolCall(id="c5", name="totally_unknown", arguments={}),
        _agent(allowed_tool_names=["totally_unknown"]),
        registry_tool_names={"wiki_note_search"},
    )
    assert d2.verdict == ToolPolicyVerdict.BLOCK

    # Matched capability subset excludes tool
    d3 = gate.evaluate(
        ToolCall(id="c6", name="cli_exec", arguments={"command": "ls"}),
        _agent(),
        registry_tool_names={"cli_exec", "wiki_note_search"},
        matched_capability_ids=["tool.wiki_note_search"],
    )
    assert d3.verdict == ToolPolicyVerdict.BLOCK


def test_req_toolpol_003_prohibited_dangerous_command_blocks(gate):
    """DangerousCommandFilter hard-BLOCK (not confirm) for prohibited patterns."""
    d = gate.evaluate(
        ToolCall(id="c7", name="cli_exec", arguments={"command": "rm -rf /"}),
        _agent(),
        registry_tool_names={"cli_exec"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert "prohibited" in d.reason.lower() or "dangerous" in d.reason.lower()


def test_req_toolpol_004_durable_policy_not_prompt_only(gate, store):
    """Policy from durable settings key tool_policy [REQ-TOOLPOL-004]."""
    store.set_setting(
        "tool_policy",
        {
            "block_tools": [],
            "require_confirm_tools": ["wiki_note_search"],
            "safe_tools": [],
        },
    )
    gate.reload_policy()
    d = gate.evaluate(
        ToolCall(id="c8", name="wiki_note_search", arguments={}),
        _agent(),
        registry_tool_names={"wiki_note_search"},
    )
    assert d.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    gate.log_decision(
        d,
        session_id="sess_log",
        agent_id="assistant",
    )
    rows = store.list_tool_policy_decisions(session_id="sess_log", limit=5)
    assert rows and rows[0]["verdict"] == "REQUIRE_CONFIRM"


def test_req_toolpol_005_extends_existing_hitl_no_parallel_engine():
    """Gate module extends HITL/filter — no ParallelHitlEngine [REQ-TOOLPOL-005]."""
    import inspect

    from src.application.safety import tool_policy_gate as mod

    src = inspect.getsource(mod)
    assert "HITLApprovalEngine" in src or "hitl" in src.lower()
    assert "DangerousCommandFilter" in src
    assert "class ParallelHitl" not in src
    assert "class AlternateHitl" not in src
