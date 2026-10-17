"""CARD-704: Staged RCA self-healing proposals on recurring tool or routine failures.

Tests:
1. `RcaProposalService` aggregates failing tool and routine spans into structured RCA proposals
   with severity, failure count, trace IDs, error details, skill/file resolution, and a
   `repair_prompt` instructing `AutoReiv` to repair via `write_skill_file` / `register_native_tool`.
2. Negative assertion: once a newer execution succeeds or the tool file is updated after the
   latest failure, the RCA proposal is automatically resolved and no longer staged.
3. `GET /api/telemetry/rca-proposals` and `POST /api/telemetry/rca-proposals/{id}/dismiss`
   persist dismissal timestamps in SQLite settings so dismissed proposals stay hidden unless
   a newer failure occurs after dismissal.
4. Capabilities Studio (`#view-capabilities`) hosts `#capabilitiesRcaProposalsPanel` and
   wires `rca_proposals_panel.js` with "Repair in Chat" and "Dismiss" actions.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.telemetry.collector import TelemetryCollector
from src.domain.telemetry.models import TelemetrySpan, utc_now
from src.infrastructure.content import store as content_store
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.observability import router as observability_router

pytestmark = pytest.mark.guard

REPO_ROOT = Path(__file__).resolve().parents[3]


def _seed_broken_skill_tool(data_dir: Path, skill_id: str = "rca-math-skill", tool_name: str = "divide_metric") -> Path:
    cstore = content_store.configure(
        data_root=data_dir,
        platform_root=REPO_ROOT / "platform",
    )
    cstore.skills.save(
        skill_id,
        {"name": "RCA Math Skill", "description": "Skill with a tool that divides numbers."},
        "# RCA Math Skill\n",
    )
    user_md = cstore.skills.user_path(skill_id)
    assert user_md is not None
    tools_dir = user_md.parent / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    tool_file = tools_dir / f"{tool_name}.py"
    tool_file.write_text(
        '"""Divide two metrics."""\n\n'
        'RISK = "read_only"\n\n'
        "def run(numerator: int = 10, denominator: int = 0) -> dict:\n"
        '    return {"ratio": numerator / denominator}\n',
        encoding="utf-8",
    )
    return tool_file


def test_rca_proposal_service_aggregates_recurring_tool_and_routine_failures(tmp_path, monkeypatch):
    from src.application.telemetry.rca_proposals import RcaProposalService

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    content_store.reset_store()
    _seed_broken_skill_tool(tmp_path, skill_id="rca-math-skill", tool_name="divide_metric")

    db_path = tmp_path / "database" / "autoreiv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    state_store = SQLiteStateStore(db_path=str(db_path))
    state_store.initialize_db()
    collector = TelemetryCollector(state_store)

    collector.record_tool_span(
        agent_id="autoreiv",
        session_id="sess-rca-1",
        tool_name="divide_metric",
        duration_ms=12.5,
        success=False,
        status="error",
        error_message="ZeroDivisionError: division by zero",
        trace_id="trace-rca-101",
        metadata={"arguments": {"numerator": 10, "denominator": 0}},
    )
    collector.record_tool_span(
        agent_id="autoreiv",
        session_id="sess-rca-2",
        tool_name="divide_metric",
        duration_ms=9.1,
        success=False,
        status="error",
        error_message="ZeroDivisionError: division by zero",
        trace_id="trace-rca-102",
        metadata={"arguments": {"numerator": 25, "denominator": 0}},
    )

    routine_span = TelemetrySpan(
        id="span-routine-fail-1",
        trace_id="trace-routine-501",
        session_id="sess-routine-1",
        agent_id="autoreiv",
        span_type="routine",
        name="nightly_digest",
        duration_ms=450.0,
        success=False,
        status="error",
        error_message="RuntimeError: upstream feed returned HTTP 502",
        metadata={"routine_id": "routine-nightly-digest"},
        created_at=utc_now(),
    )
    state_store.save_telemetry_span(routine_span)

    service = RcaProposalService(
        store=state_store,
        content_store=content_store.get_store(),
    )
    proposals = service.list_proposals()
    by_id = {p["id"]: p for p in proposals}

    assert "rca:tool:divide_metric" in by_id
    tool_prop = by_id["rca:tool:divide_metric"]
    assert tool_prop["kind"] == "tool"
    assert tool_prop["target_name"] == "divide_metric"
    assert tool_prop["skill_id"] == "rca-math-skill"
    assert tool_prop["file_path"] == "tools/divide_metric.py"
    assert tool_prop["failure_count"] == 2
    assert tool_prop["severity"] in ("high", "critical")
    assert "ZeroDivisionError" in tool_prop["latest_error"]
    assert "trace-rca-102" in tool_prop["trace_ids"]
    assert "trace-rca-101" in tool_prop["trace_ids"]
    assert "write_skill_file" in tool_prop["repair_prompt"]
    assert "rca-math-skill" in tool_prop["repair_prompt"]
    assert "tools/divide_metric.py" in tool_prop["repair_prompt"]
    assert "trace-rca-102" in tool_prop["repair_prompt"]

    assert "rca:routine:nightly_digest" in by_id
    routine_prop = by_id["rca:routine:nightly_digest"]
    assert routine_prop["kind"] == "routine"
    assert routine_prop["target_name"] == "nightly_digest"
    assert routine_prop["failure_count"] == 1
    assert "HTTP 502" in routine_prop["latest_error"]


def test_rca_proposal_resolved_when_newer_execution_succeeds(tmp_path, monkeypatch):
    from src.application.telemetry.rca_proposals import RcaProposalService

    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    content_store.reset_store()
    _seed_broken_skill_tool(tmp_path, skill_id="rca-math-skill", tool_name="divide_metric")

    db_path = tmp_path / "database" / "autoreiv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    state_store = SQLiteStateStore(db_path=str(db_path))
    state_store.initialize_db()

    t0 = utc_now() - timedelta(seconds=30)
    t1 = utc_now()
    state_store.save_telemetry_span(
        TelemetrySpan(
            id="span-fail-old",
            trace_id="trace-old",
            session_id="sess-1",
            agent_id="autoreiv",
            span_type="tool",
            name="divide_metric",
            duration_ms=5.0,
            success=False,
            status="error",
            error_message="ZeroDivisionError: division by zero",
            created_at=t0,
        )
    )
    service = RcaProposalService(store=state_store, content_store=content_store.get_store())
    assert any(p["id"] == "rca:tool:divide_metric" for p in service.list_proposals())

    # Negative assertion: once a newer execution succeeds, the proposal is resolved
    state_store.save_telemetry_span(
        TelemetrySpan(
            id="span-ok-new",
            trace_id="trace-new",
            session_id="sess-1",
            agent_id="autoreiv",
            span_type="tool",
            name="divide_metric",
            duration_ms=4.0,
            success=True,
            status="ok",
            created_at=t1,
        )
    )
    assert not any(p["id"] == "rca:tool:divide_metric" for p in service.list_proposals())


def test_rca_proposals_api_and_dismiss_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    content_store.reset_store()
    _seed_broken_skill_tool(tmp_path, skill_id="rca-math-skill", tool_name="divide_metric")

    db_path = tmp_path / "database" / "autoreiv.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    state_store = SQLiteStateStore(db_path=str(db_path))
    state_store.initialize_db()
    collector = TelemetryCollector(state_store)
    collector.record_tool_span(
        agent_id="autoreiv",
        session_id="sess-api-1",
        tool_name="divide_metric",
        duration_ms=7.0,
        success=False,
        status="error",
        error_message="ZeroDivisionError: division by zero",
        trace_id="trace-api-99",
    )

    app = FastAPI()
    app.state.store = state_store
    app.include_router(observability_router)
    client = TestClient(app)

    res = client.get("/api/telemetry/rca-proposals")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["proposals"][0]["id"] == "rca:tool:divide_metric"

    dismiss_res = client.post("/api/telemetry/rca-proposals/rca:tool:divide_metric/dismiss")
    assert dismiss_res.status_code == 200
    assert dismiss_res.json()["dismissed"] is True

    after_res = client.get("/api/telemetry/rca-proposals")
    assert after_res.status_code == 200
    assert after_res.json()["count"] == 0


def test_capabilities_studio_renders_rca_proposals_panel_and_repair_in_chat_button():
    html = (REPO_ROOT / "src/web/templates/index.html").read_text(encoding="utf-8")
    cap_start = html.index('id="view-capabilities"')
    cap_html = html[cap_start:]
    assert 'id="capabilitiesRcaProposalsPanel"' in cap_html
    assert 'data-testid="rca-proposals-panel"' in cap_html

    panel_js = (REPO_ROOT / "src/web/static/modules/studios/rca_proposals_panel.js").read_text(encoding="utf-8")
    assert "export function renderRcaProposalsHtml" in panel_js
    assert "export function setupRcaProposalsPanel" in panel_js
    assert "data-rca-repair" in panel_js
    assert "data-rca-dismiss" in panel_js

    cap_js = (REPO_ROOT / "src/web/static/modules/studios/capabilities_studio.js").read_text(encoding="utf-8")
    assert "setupRcaProposalsPanel" in cap_js
