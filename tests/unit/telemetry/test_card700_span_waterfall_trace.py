"""CARD-700 tests: hierarchical span waterfall tracing, credential scrubbing, JSONL export, and /api/traces."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from src.application.orchestration.session_activity import build_session_journey
from src.application.telemetry.collector import TelemetryCollector
from src.application.telemetry.span_waterfall import (
    TraceWriter,
    build_trace_waterfall,
    format_trace,
    list_traces,
    load_spans,
    scrub_text,
    scrub_value,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def test_scrub_text_and_value_redact_credentials_without_damaging_short_words():
    secret = "sk-live-9876543210abcdef"
    assert scrub_text(f"Bearer {secret} failed", secret) == "Bearer [redacted] failed"
    # Short secrets (< 8 chars) are never replaced to avoid corrupting normal prose
    assert scrub_text("cat in the hat", "cat") == "cat in the hat"

    nested = {
        "tool": "http_fetch",
        "api_key": "my-secret-api-key-value",
        "headers": {
            "Authorization": f"Bearer {secret}",
            "Accept": "application/json",
        },
        "notes": [f"token={secret}", "normal text"],
    }
    scrubbed = scrub_value(nested, secret)
    serialized = json.dumps(scrubbed)
    assert secret not in serialized
    assert "my-secret-api-key-value" not in serialized
    assert "[redacted]" in serialized
    assert scrubbed["headers"]["Accept"] == "application/json"


def test_trace_writer_writes_parent_child_jsonl_and_formats_waterfall(tmp_path: Path):
    trace_file = tmp_path / "traces" / "trace-700-unit.jsonl"
    secret = "vllm-secret-token-xyz98765"
    writer = TraceWriter(trace_file, trace_id="trace-700-unit", cover=secret)

    with writer.span("turn", session_id="sess-1", agent_id="autoreiv"):
        with writer.span("user_input", text="Read config with token " + secret):
            pass
        with writer.span("compaction", outcome="skipped"):
            pass
        with writer.span("model_request", model="qwen3.8:latest", message_count=4):
            with writer.span("model_response", model="qwen3.8:latest", finish_reason="tool_calls"):
                pass
        with writer.span("tool_call", tool="read_project_file", path="README.md"):
            with writer.span("tool_result", tool="read_project_file", status="ok"):
                pass
        with writer.span("final_answer", finish_reason="stop"):
            pass

    assert trace_file.is_file()
    raw_jsonl = trace_file.read_text(encoding="utf-8")
    assert secret not in raw_jsonl
    assert "[redacted]" in raw_jsonl

    spans = load_spans(trace_file)
    names = [s["name"] for s in spans]
    for expected in (
        "turn",
        "user_input",
        "compaction",
        "model_request",
        "model_response",
        "tool_call",
        "tool_result",
        "final_answer",
    ):
        assert expected in names

    by_name = {s["name"]: s for s in spans}
    assert by_name["turn"]["parent_span_id"] is None
    assert by_name["user_input"]["parent_span_id"] == by_name["turn"]["span_id"]
    assert by_name["model_request"]["parent_span_id"] == by_name["turn"]["span_id"]
    assert by_name["model_response"]["parent_span_id"] == by_name["model_request"]["span_id"]
    assert by_name["tool_call"]["parent_span_id"] == by_name["turn"]["span_id"]
    assert by_name["tool_result"]["parent_span_id"] == by_name["tool_call"]["span_id"]

    rendered = format_trace(spans, full=True)
    assert "turn" in rendered
    assert "  model_request" in rendered
    assert "    model_response" in rendered
    assert "  tool_call" in rendered
    assert "    tool_result" in rendered
    assert secret not in rendered


def test_collector_records_scrubbed_waterfall_and_session_journey_exposes_it():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_data_dir = os.environ.get("AUTOREIV_DATA_DIR")
        os.environ["AUTOREIV_DATA_DIR"] = tmpdir
        try:
            db_path = os.path.join(tmpdir, "database", "autoreiv.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            store = SQLiteStateStore(db_path=db_path)
            collector = TelemetryCollector(store)

            sess = store.create_session(agent_id="autoreiv", title="CARD-700 Trace Session")
            leak_secret = "sk-proj-secret-credential-999999"

            turn_span = collector.record_turn_span(
                agent_id="autoreiv",
                session_id=sess.id,
                model="qwen3.8:latest",
                provider="ollama",
                duration_ms=420.5,
                ttft_ms=85.2,
                prompt_tokens=310,
                completion_tokens=64,
                success=True,
                trace_id=sess.id,
                metadata={
                    "token_breakdown": {
                        "user_prompt": 40,
                        "compacted_history": 120,
                        "completion": 64,
                    },
                    "timing_breakdown": {
                        "harness_prep_ms": 18.4,
                        "ttft_ms": 85.2,
                        "llm_generation_ms": 402.1,
                        "total_round_trip_ms": 420.5,
                    },
                    "api_key": leak_secret,
                },
            )
            collector.record_tool_span(
                agent_id="autoreiv",
                session_id=sess.id,
                tool_name="active_project_info",
                duration_ms=34.8,
                success=True,
                status="ok",
                trace_id=sess.id,
                parent_span_id=turn_span.id,
                metadata={
                    "payload_bytes": 256,
                    "arguments": {"authorization": f"Bearer {leak_secret}"},
                },
            )

            traces = list_traces(store, session_id=sess.id)
            assert len(traces) >= 1
            assert traces[0]["session_id"] == sess.id

            waterfall = build_trace_waterfall(store, sess.id)
            assert waterfall is not None
            span_names = [s["name"] for s in waterfall["spans"]]
            for stage in (
                "turn",
                "user_input",
                "compaction",
                "model_request",
                "model_response",
                "tool_call",
                "tool_result",
                "final_answer",
            ):
                assert stage in span_names, f"Missing stage {stage} in {span_names}"

            serialized = json.dumps(waterfall)
            assert leak_secret not in serialized
            assert "[redacted]" in serialized
            assert Path(waterfall["jsonl_path"]).is_file()

            journey = build_session_journey(store, sess.id)
            assert "trace_waterfall" in journey
            assert len(journey["trace_waterfall"]["spans"]) >= 7
        finally:
            if old_data_dir is None:
                os.environ.pop("AUTOREIV_DATA_DIR", None)
            else:
                os.environ["AUTOREIV_DATA_DIR"] = old_data_dir
