"""Unit tests for Observability Audit Endpoints [CARD-337].

Verifies /api/observability/sessions, /api/observability/audit,
and /api/observability/audit/export endpoints.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.telemetry.collector import TelemetryCollector
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.observability import router as obs_router


@pytest.fixture
def obs_client_fixture(tmp_path):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    collector = TelemetryCollector(store=store)

    # Create dummy session
    session = store.create_session(agent_id="assistant", title="Test Optimization Session")

    # Record span for session with token breakdown
    collector.record_turn_span(
        agent_id="assistant",
        session_id=session.id,
        duration_ms=2500.0,
        prompt_tokens=1500,
        completion_tokens=120,
        success=True,
        metadata={
            "token_breakdown": {
                "user_prompt": 100,
                "agent_persona": 300,
                "tool_schemas": 1000,
                "completion": 120,
                "total_prompt_tokens": 1500,
                "total_tokens": 1620,
                "scaffold_tokens": 1400,
                "scaffold_ratio": 14.0,
            },
            "timing_breakdown": {
                "harness_prep_ms": 5.0,
                "ttft_ms": 450.0,
                "generation_ms": 2045.0,
                "tokens_per_second": 58.7,
            },
        },
    )

    wiki_service_mock = MagicMock()
    wiki_service_mock.create_note.return_value = {
        "success": True,
        "path": f"00_Inbox/performance_audit_{session.id}.md",
    }

    app = FastAPI()
    app.state.store = store
    app.state.obs_service = MagicMock()
    app.state.wiki_service = wiki_service_mock
    app.include_router(obs_router)

    client = TestClient(app)
    return client, session, wiki_service_mock


def test_get_observability_sessions(obs_client_fixture):
    client, session, _ = obs_client_fixture
    res = client.get("/api/observability/sessions?agent_id=assistant")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["id"] == session.id
    assert data[0]["agent_id"] == "assistant"
    assert data[0]["title"] == "Test Optimization Session"


def test_get_observability_audit(obs_client_fixture):
    client, session, _ = obs_client_fixture
    res = client.get(f"/api/observability/audit?session_id={session.id}")
    assert res.status_code == 200
    data = res.json()
    assert "report" in data
    assert "markdown" in data
    report = data["report"]
    assert report["target_type"] == "session"
    assert report["target_id"] == session.id
    assert report["total_tokens"] == 1620
    assert report["scaffold_ratio"] == 14.0
    assert "# Performance & Cost Audit" in data["markdown"]


def test_export_observability_audit_to_inbox(obs_client_fixture):
    client, session, wiki_mock = obs_client_fixture
    payload = {
        "session_id": session.id,
        "title": "Custom Performance Audit Title",
    }
    res = client.post("/api/observability/audit/export", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Custom Performance Audit Title" in data["title"]
    assert "00_Inbox" in data["path"]

    assert wiki_mock.create_note.called
    kwargs = wiki_mock.create_note.call_args.kwargs
    assert kwargs["category"] == "inbox"
    assert kwargs["domain"] == "engineering"
    assert kwargs["topic"] == "performance"
    assert "performance" in kwargs["tags"]
