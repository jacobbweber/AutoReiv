"""Unit & Operator Contract Tests for Observability Journey Canvas [CARD-428].

Verifies:
1. JourneyCanvasService scenario catalog and step assembly.
2. Canonical scenarios across 4 swimlanes (UI, API, Orchestrator, Storage).
3. Synchronized source snippet extraction with line bounds and highlighting.
4. Security boundary invariant: Path traversal outside repo root is strictly forbidden.
5. FastAPI endpoints: /scenarios, /scenarios/{id}, /source.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.observability.journey_canvas import (
    JourneyCanvasService,
    JourneyScenario,
    SourceSnippetResponse,
)
from src.web.routers.observability import router as obs_router


@pytest.fixture
def journey_service():
    return JourneyCanvasService()


@pytest.fixture
def obs_client():
    app = FastAPI()
    app.include_router(obs_router)
    return TestClient(app)


# =========================================================================
# 1. Service Domain Tests
# =========================================================================

def test_list_scenarios_returns_canonical_catalog(journey_service: JourneyCanvasService):
    scenarios = journey_service.list_scenarios()
    assert isinstance(scenarios, list)
    assert len(scenarios) >= 3

    ids = [s.id for s in scenarios]
    assert "chat_turn_hitl_approval" in ids
    assert "routine_wiki_execution" in ids
    assert "react_multi_turn_reasoning" in ids

    # Validate schema of each catalog entry
    for s in scenarios:
        assert s.id
        assert s.title
        assert s.description
        assert s.step_count > 0
        assert s.category in {"chat", "routine", "react", "system"}


def test_get_scenario_chat_turn_hitl_approval(journey_service: JourneyCanvasService):
    scenario = journey_service.get_scenario("chat_turn_hitl_approval")
    assert scenario is not None
    assert isinstance(scenario, JourneyScenario)
    assert scenario.id == "chat_turn_hitl_approval"
    assert len(scenario.steps) >= 4

    # Verify all 4 architectural swimlanes are covered
    swimlanes = {step.swimlane for step in scenario.steps}
    assert "ui" in swimlanes
    assert "api" in swimlanes
    assert "orchestrator" in swimlanes
    assert "storage" in swimlanes

    # Find the HITL pause step and verify invariants
    hitl_steps = [
        s for s in scenario.steps
        if "hitl" in s.id.lower() or "hitl" in s.title.lower() or "approval" in s.title.lower() or "awaiting_approval" in s.state_transition.lower()
    ]
    assert len(hitl_steps) >= 1
    hitl_step = hitl_steps[0]
    assert hitl_step.swimlane in {"orchestrator", "storage"}
    assert "AWAITING_APPROVAL" in hitl_step.state_transition
    assert hitl_step.source_file.endswith(".py")
    assert hitl_step.source_line > 0
    assert isinstance(hitl_step.payload, dict)


def test_get_scenario_unknown_id_returns_none(journey_service: JourneyCanvasService):
    assert journey_service.get_scenario("unknown_random_scenario_xyz") is None


def test_get_source_snippet_valid_file(journey_service: JourneyCanvasService):
    # Test loading real known file in repo
    res = journey_service.get_source_snippet("src/domain/telemetry/models.py", line=15, range_lines=5)
    assert isinstance(res, SourceSnippetResponse)
    assert res.exists is True
    assert res.file_path == "src/domain/telemetry/models.py"
    assert res.highlight_line == 15
    assert res.start_line <= 15 <= res.end_line
    assert len(res.lines) > 0
    assert res.language == "python"

    # Verify that the lines contain line numbers and code
    target_line_entry = next((line_item for line_item in res.lines if line_item.line_number == 15), None)
    assert target_line_entry is not None
    assert "TelemetrySpan" in target_line_entry.content or "class" in target_line_entry.content


def test_get_source_snippet_security_path_traversal_rejection(journey_service: JourneyCanvasService):
    """Negative Assertion: File paths outside repo checkout root MUST be refused."""
    traversal_paths = [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "../secret.env",
        "/etc/shadow",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
    ]
    for bad_path in traversal_paths:
        with pytest.raises((ValueError, PermissionError)):
            journey_service.get_source_snippet(bad_path, line=1)


# =========================================================================
# 2. FastAPI Endpoint Tests
# =========================================================================

def test_api_list_scenarios(obs_client: TestClient):
    resp = obs_client.get("/api/observability/journey-canvas/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    first = data[0]
    assert "id" in first
    assert "title" in first
    assert "step_count" in first


def test_api_get_scenario_success(obs_client: TestClient):
    resp = obs_client.get("/api/observability/journey-canvas/scenarios/chat_turn_hitl_approval")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "chat_turn_hitl_approval"
    assert "steps" in data
    assert len(data["steps"]) >= 4


def test_api_get_scenario_not_found(obs_client: TestClient):
    resp = obs_client.get("/api/observability/journey-canvas/scenarios/non_existent_scenario_123")
    assert resp.status_code == 404
    err = resp.json()
    assert "error" in err or "detail" in err


def test_api_get_source_snippet_success(obs_client: TestClient):
    resp = obs_client.get(
        "/api/observability/journey-canvas/source",
        params={"file_path": "src/domain/telemetry/models.py", "line": 15, "range_lines": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["exists"] is True
    assert data["highlight_line"] == 15
    assert len(data["lines"]) > 0


def test_api_get_source_snippet_path_traversal_blocked(obs_client: TestClient):
    """Negative Assertion: API must return 400 or 403 on traversal attempt."""
    resp = obs_client.get(
        "/api/observability/journey-canvas/source",
        params={"file_path": "../../etc/passwd", "line": 1},
    )
    assert resp.status_code in {400, 403}
