"""
Unit tests for TraceExporter & Structured JSON Export [REQ-OBS-005, REQ-OBS-006].
"""

import json
from datetime import datetime, timezone

import pytest

from src.application.observability.exporter import TraceExporter
from src.domain.telemetry.models import TelemetrySpan
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def test_export_spans_to_json():
    now = datetime.now(timezone.utc)
    spans = [
        TelemetrySpan(
            id="span-1",
            agent_id="librarian",
            session_id="sess-abc",
            span_type="turn",
            name="turn",
            created_at=now,
            duration_ms=120.0,
            success=True,
            prompt_tokens=40,
            completion_tokens=20,
        )
    ]

    json_str = TraceExporter.export_spans_to_json(spans)
    data = json.loads(json_str)

    assert "spans" in data
    assert len(data["spans"]) == 1
    assert data["spans"][0]["id"] == "span-1"
    assert data["spans"][0]["agent_id"] == "librarian"
    assert data["spans"][0]["total_tokens"] == 60


def test_export_session_traces_from_store(store):
    now = datetime.now(timezone.utc)
    store.save_telemetry_span(
        TelemetrySpan(
            id="s1",
            session_id="sess-export",
            agent_id="general-assistant",
            span_type="turn",
            name="turn",
            created_at=now,
            success=True,
        )
    )
    store.save_telemetry_span(
        TelemetrySpan(
            id="s2",
            session_id="sess-other",
            agent_id="general-assistant",
            span_type="turn",
            name="turn",
            created_at=now,
            success=True,
        )
    )

    json_out = TraceExporter.export_session_traces(store, session_id="sess-export")
    data = json.loads(json_out)

    assert len(data["spans"]) == 1
    assert data["spans"][0]["id"] == "s1"
