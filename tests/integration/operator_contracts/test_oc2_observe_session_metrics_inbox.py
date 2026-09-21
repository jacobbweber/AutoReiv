"""OC-2: Observe per-agent chat session metrics → non-empty inbox [CARD-412 / ADR-0055].

Locks: seed telemetry in DB → POST audit/export → 00_Inbox note exists with non-empty body
and expected metric fields. Negative: empty success theater must fail.
"""

from __future__ import annotations

from src.application.telemetry.collector import TelemetryCollector


def test_oc2_observe_session_metrics_export_writes_nonempty_inbox(operator_client):
    client, store, wiki = operator_client

    session = store.create_session(agent_id="assistant", title="OC2 Metrics Session")
    collector = TelemetryCollector(store=store)
    collector.record_turn_span(
        agent_id="assistant",
        session_id=session.id,
        model="qwen3:8b",
        provider="ollama",
        duration_ms=2500.0,
        ttft_ms=450.0,
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
                "ttft_ms": 450.0,
                "tokens_per_second": 58.7,
            },
        },
    )

    spans = store.get_telemetry_spans(session_id=session.id, limit=10)
    assert spans, "seed failed: no telemetry spans in DB"
    assert sum(s.prompt_tokens + s.completion_tokens for s in spans) >= 1620

    audit = client.get(f"/api/observability/audit?session_id={session.id}")
    assert audit.status_code == 200
    assert audit.json()["report"]["total_tokens"] == 1620

    export = client.post(
        "/api/observability/audit/export",
        json={"session_id": session.id, "title": "OC2 Per-Agent Session Metrics Report"},
    )
    assert export.status_code == 200, export.text
    data = export.json()
    assert data.get("success") is True
    path = data["path"]
    assert path.replace("\\", "/").startswith("00_Inbox/"), path

    note = client.get(f"/api/wiki/note?path={path}")
    assert note.status_code == 200, note.text
    note_data = note.json()
    content = (note_data.get("content") or "").strip()

    assert content, "OC-2 FAIL: inbox note body is empty despite DB metrics"
    assert len(content) > 80, f"OC-2 FAIL: inbox note body too thin ({len(content)} chars)"

    lowered = content.lower()
    assert "total tokens" in lowered or "1,620" in content or "1620" in content
    assert "prompt" in lowered
    assert session.id[:8] in content or "session" in lowered

    disk = wiki.joinpath(*path.split("/"))
    assert disk.is_file(), f"missing note file {disk}"
    raw = disk.read_text(encoding="utf-8")
    assert "Performance" in raw or "Audit" in raw
    body_after_fm = raw.split("---", 2)[-1].strip() if raw.startswith("---") else raw.strip()
    assert body_after_fm, "OC-2 FAIL: on-disk note has frontmatter only (empty body)"

    # Export API itself must report non-empty body (no success theater)
    assert int(data.get("body_chars") or 0) > 80
