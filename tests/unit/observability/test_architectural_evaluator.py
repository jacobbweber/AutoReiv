"""
Unit tests for ArchitecturalEvaluatorService [CARD-364 / REQ-ARCH-001..006].
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.application.observability.architectural_evaluator import ArchitecturalEvaluatorService
from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.models import ArchitecturalThresholdType
from src.domain.telemetry.models import TelemetrySpan


def _utc_now():
    return datetime.now(timezone.utc)


def test_evaluator_service_scans_sessions_and_spans(tmp_path):
    """Verify ArchitecturalEvaluatorService orchestrates detection across sessions and telemetry spans."""
    mock_store = MagicMock()

    # Create mock session
    mock_sess = MagicMock()
    mock_sess.id = "sess-arch-1"
    mock_sess.agent_id = "autoreiv"
    mock_sess.updated_at = _utc_now().isoformat()
    mock_store.list_sessions.return_value = [mock_sess]

    # Create mock messages for session
    mock_store.get_messages.return_value = [
        ChatMessage(role=Role.USER, content="Scrape and execute"),
        ChatMessage(role=Role.TOOL, name="web_search", content="search results"),
        ChatMessage(role=Role.TOOL, name="cli_exec", content="rm -rf /test"),
    ]

    # Create mock telemetry span
    mock_span = TelemetrySpan(
        id="span-test-1",
        session_id="sess-arch-1",
        agent_id="autoreiv",
        span_type="turn",
        name="agent_turn",
        metadata={"active_tool_count": 10, "tool_schema_chars": 5000},
    )
    mock_store.get_telemetry_spans.return_value = [mock_span]

    service = ArchitecturalEvaluatorService(store=mock_store, data_dir=tmp_path)
    report = service.scan_history(lookback_hours=24)

    assert report.scanned_sessions == 1
    assert report.scanned_spans == 1
    assert report.alert_count >= 3  # TOOL_BLOAT, CONTEXT_TAX, SECURITY_COLLISION, COGNITIVE_CONFLICT
    assert report.clean is False

    # Check alert types present
    alert_types = {a.threshold_type for a in report.alerts}
    assert ArchitecturalThresholdType.TOOL_BLOAT in alert_types
    assert ArchitecturalThresholdType.CONTEXT_TAX in alert_types
    assert ArchitecturalThresholdType.SECURITY_COLLISION in alert_types


def test_evaluator_service_persists_and_lists_alerts(tmp_path):
    """Verify alerts are cached and can be queried with filters."""
    mock_store = MagicMock()
    mock_store.list_sessions.return_value = []
    mock_span = TelemetrySpan(
        id="span-test-2",
        session_id="sess-arch-2",
        agent_id="autoreiv",
        span_type="turn",
        name="agent_turn",
        metadata={"active_tool_count": 12},
    )
    mock_store.get_telemetry_spans.return_value = [mock_span]

    service = ArchitecturalEvaluatorService(store=mock_store, data_dir=tmp_path)
    service.scan_history(lookback_hours=24)

    # Filter by threshold type
    bloat_alerts = service.list_alerts(threshold_type=ArchitecturalThresholdType.TOOL_BLOAT)
    assert len(bloat_alerts) >= 1
    assert bloat_alerts[0].threshold_type == ArchitecturalThresholdType.TOOL_BLOAT

    # Filter by severity
    high_alerts = service.list_alerts(severity="high")
    assert len(high_alerts) >= 1
    assert high_alerts[0].severity == "high"
