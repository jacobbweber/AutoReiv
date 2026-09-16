"""Unit tests for audit_performance_and_cost Tool [CARD-337 / REQ-AUDIT-002].

Verifies tool execution for job, session, and window targets,
markdown report return, and wiki note export handoff.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.observability.audit_service import AuditService
from src.application.skills.audit_tools import AuditTools
from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def audit_tool_fixture():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    collector = TelemetryCollector(store=store)

    wiki_tools_mock = MagicMock()
    wiki_tools_mock.create_wiki_note.return_value = {
        "success": True,
        "path": "01_Engineering/Performance/20260916_job_101.md",
    }

    audit_service = AuditService(store=store)
    tools = AuditTools(store=store, audit_service=audit_service, wiki_tools=wiki_tools_mock)
    registry = ScopedToolRegistry()
    tools.register_tools(registry)

    return store, collector, tools, wiki_tools_mock, registry


def test_tool_registration(audit_tool_fixture):
    _, _, _, _, registry = audit_tool_fixture
    assert "audit_performance_and_cost" in registry
    defn = registry.get_tool_definition("audit_performance_and_cost")
    assert defn is not None
    assert "target_type" in defn.parameters["properties"]
    assert "export_to_wiki" in defn.parameters["properties"]


def test_audit_job_tool_execution(audit_tool_fixture):
    store, collector, tools, wiki_tools_mock, _ = audit_tool_fixture
    job_id = "job_audit_999"

    collector.record_turn_span(
        agent_id="assistant",
        session_id="sess_tool_test",
        duration_ms=3000.0,
        prompt_tokens=2000,
        completion_tokens=100,
        success=True,
        metadata={
            "step_context": {"job_id": job_id},
            "token_breakdown": {
                "user_prompt": 100,
                "agent_persona": 400,
                "tool_schemas": 1500,
                "completion": 100,
                "total_prompt_tokens": 2000,
                "total_tokens": 2100,
                "scaffold_tokens": 1900,
                "scaffold_ratio": 19.0,
            },
        },
    )

    res = tools.audit_performance_and_cost(
        target_type="job",
        target_id=job_id,
        export_to_wiki=True,
        wiki_title="Job 999 Performance Audit",
    )

    assert res["success"] is True
    assert res["target_type"] == "job"
    assert res["target_id"] == job_id
    assert res["total_turns"] == 1
    assert res["total_tokens"] == 2100
    assert res["scaffold_ratio"] == 19.0
    assert res["estimated_cost_usd"] > 0
    assert "# Performance & Cost Audit" in res["report_markdown"]
    assert "job_audit_999" in res["report_markdown"]

    # Verify wiki export handoff
    assert wiki_tools_mock.create_wiki_note.called
    call_kwargs = wiki_tools_mock.create_wiki_note.call_args.kwargs
    assert call_kwargs["title"] == "Job 999 Performance Audit"
    assert "01_Engineering/Performance/" in call_kwargs["relative_path"]
    assert call_kwargs["domain"] == "engineering"


def test_audit_window_tool_execution(audit_tool_fixture):
    store, collector, tools, wiki_tools_mock, _ = audit_tool_fixture

    collector.record_turn_span(
        agent_id="direct",
        session_id="sess_win_test",
        duration_ms=1000.0,
        prompt_tokens=50,
        completion_tokens=25,
        metadata={
            "token_breakdown": {
                "user_prompt": 25,
                "agent_persona": 25,
                "total_prompt_tokens": 50,
                "total_tokens": 75,
                "scaffold_tokens": 25,
                "scaffold_ratio": 1.0,
            }
        },
    )

    res = tools.audit_performance_and_cost(
        target_type="window",
        target_id="24",
        export_to_wiki=False,
    )

    assert res["success"] is True
    assert res["target_type"] == "window"
    assert res["total_turns"] >= 1
    assert not wiki_tools_mock.create_wiki_note.called


def test_audit_invalid_target_type(audit_tool_fixture):
    _, _, tools, _, _ = audit_tool_fixture
    res = tools.audit_performance_and_cost(target_type="unsupported_type")
    assert res["success"] is False
    assert "Invalid target_type" in res["error"]
