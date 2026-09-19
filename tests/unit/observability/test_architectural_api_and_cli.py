"""
Unit tests for Architectural Telemetry REST API and CLI [CARD-364 / REQ-ARCH-006, REQ-ARCH-007].
"""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.cli.main import main
from src.domain.observability.models import (
    ArchitecturalAlert,
    ArchitecturalScanReport,
    ArchitecturalThresholdType,
)
from src.web.app import create_app


def test_rest_api_architectural_scan():
    """[REQ-ARCH-006] Test POST /api/observability/architectural/scan triggers audit and returns report."""
    app = create_app()
    client = TestClient(app)

    mock_report = ArchitecturalScanReport(
        scanned_sessions=5,
        scanned_spans=12,
        alert_count=1,
        alerts_by_type={"tool_bloat": 1},
        alerts=[
            ArchitecturalAlert(
                id="alert-1",
                threshold_type=ArchitecturalThresholdType.TOOL_BLOAT,
                severity="high",
                agent_id="autoreiv",
                session_id="s-1",
                evidence="Turn mounted 10 tools (> 8)",
                remediation_proposal="Decompose skill",
            )
        ],
        clean=False,
    )

    with patch(
        "src.application.observability.architectural_evaluator.ArchitecturalEvaluatorService.scan_history",
        return_value=mock_report,
    ):
        response = client.post(
            "/api/observability/architectural/scan",
            json={"lookback_hours": 12, "session_limit": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["scanned_sessions"] == 5
        assert data["alert_count"] == 1
        assert data["clean"] is False
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["threshold_type"] == "tool_bloat"


def test_rest_api_architectural_alerts_listing():
    """[REQ-ARCH-006] Test GET /api/observability/architectural/alerts supports filtering."""
    app = create_app()
    client = TestClient(app)

    mock_alerts = [
        ArchitecturalAlert(
            id="alert-sec-1",
            threshold_type=ArchitecturalThresholdType.SECURITY_COLLISION,
            severity="critical",
            agent_id="autoreiv",
            session_id="s-sec",
            evidence="web_search + cli_exec",
            remediation_proposal="Gated",
        )
    ]

    with patch(
        "src.application.observability.architectural_evaluator.ArchitecturalEvaluatorService.list_alerts",
        return_value=mock_alerts,
    ):
        response = client.get("/api/observability/architectural/alerts?severity=critical")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["threshold_type"] == "security_collision"


def test_cli_scan_architecture_clean(capsys):
    """[REQ-ARCH-007] Test autoreiv scan-architecture outputs clean summary when no breaches."""
    mock_report = ArchitecturalScanReport(
        scanned_sessions=2,
        scanned_spans=4,
        alert_count=0,
        alerts=[],
        clean=True,
    )

    with patch(
        "src.application.observability.architectural_evaluator.ArchitecturalEvaluatorService.scan_history",
        return_value=mock_report,
    ):
        exit_code = main(["scan-architecture", "--days", "1"])
        captured = capsys.readouterr()

        assert exit_code == 0
        assert "Architectural Telemetry & Threshold Scanner" in captured.out
        assert "within God-Agent architectural thresholds" in captured.out


def test_cli_scan_architecture_json(capsys):
    """[REQ-ARCH-007] Test autoreiv scan-architecture --json outputs valid JSON report."""
    mock_report = ArchitecturalScanReport(
        scanned_sessions=3,
        scanned_spans=8,
        alert_count=0,
        alerts=[],
        clean=True,
    )

    with patch(
        "src.application.observability.architectural_evaluator.ArchitecturalEvaluatorService.scan_history",
        return_value=mock_report,
    ):
        exit_code = main(["scan-architecture", "--json"])
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["scanned_sessions"] == 3
        assert data["clean"] is True


def test_cli_scan_architecture_breach_exit_code(capsys):
    """[REQ-ARCH-007] Test autoreiv scan-architecture exits 1 on architectural breach."""
    mock_report = ArchitecturalScanReport(
        scanned_sessions=1,
        scanned_spans=2,
        alert_count=1,
        alerts=[
            ArchitecturalAlert(
                id="alert-crit-1",
                threshold_type=ArchitecturalThresholdType.SECURITY_COLLISION,
                severity="critical",
                agent_id="autoreiv",
                evidence="untrusted with mutating lever",
                remediation_proposal="Add HITL",
            )
        ],
        clean=False,
    )

    with patch(
        "src.application.observability.architectural_evaluator.ArchitecturalEvaluatorService.scan_history",
        return_value=mock_report,
    ):
        exit_code = main(["scan-architecture"])
        captured = capsys.readouterr()

        assert exit_code == 1
        assert "SECURITY_COLLISION" in captured.out
        assert "threshold breaches detected" in captured.out
