"""
Unit tests for CARD-364: Architectural Telemetry & Threshold Detectors.
Grounded in ADR-0054 [REQ-ARCH-001..005].
"""

from datetime import datetime, timezone

from src.domain.gateway.models import ChatMessage, Role
from src.domain.observability.architectural_detector import ArchitecturalThresholdDetector
from src.domain.observability.models import (
    ArchitecturalThresholdType,
)


def _utc_now():
    return datetime.now(timezone.utc)


def test_detect_tool_bloat_triggers_on_exceeded_entropy():
    """[REQ-ARCH-001] Detect when active tools exceed the Rule of 7 budget (>8 tools)."""
    detector = ArchitecturalThresholdDetector(max_active_tools=8)
    span = {
        "span_id": "span-1",
        "session_id": "sess-1",
        "agent_id": "autoreiv",
        "active_tool_count": 10,
        "tool_schema_chars": 1200,
        "start_time": _utc_now(),
    }

    alerts = detector.evaluate_turn_span(span)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.threshold_type == ArchitecturalThresholdType.TOOL_BLOAT
    assert alert.severity == "high"
    assert "10 tools" in alert.evidence
    assert "Rule of 7" in alert.remediation_proposal


def test_detect_tool_bloat_clean_when_under_budget():
    """[REQ-ARCH-001] No alert when active tools are within the 8-tool ceiling."""
    detector = ArchitecturalThresholdDetector(max_active_tools=8)
    span = {
        "span_id": "span-2",
        "session_id": "sess-1",
        "agent_id": "autoreiv",
        "active_tool_count": 5,
        "tool_schema_chars": 1100,
        "start_time": _utc_now(),
    }

    alerts = detector.evaluate_turn_span(span)
    assert len(alerts) == 0


def test_detect_context_tax_triggers_on_large_schema():
    """[REQ-ARCH-002] Detect when tool schema pre-fill exceeds character budget (>4,000 chars)."""
    detector = ArchitecturalThresholdDetector(max_schema_chars=4000)
    span = {
        "span_id": "span-3",
        "session_id": "sess-1",
        "agent_id": "autoreiv",
        "active_tool_count": 6,
        "tool_schema_chars": 5800,
        "start_time": _utc_now(),
    }

    alerts = detector.evaluate_turn_span(span)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.threshold_type == ArchitecturalThresholdType.CONTEXT_TAX
    assert alert.severity == "medium"
    assert "5800 characters" in alert.evidence
    assert "demand-paged" in alert.remediation_proposal.lower()


def test_detect_security_collision_untrusted_input_with_mutating_tools():
    """[REQ-ARCH-003] Detect untrusted input co-mingled with mutating host tools without HITL."""
    detector = ArchitecturalThresholdDetector()
    messages = [
        ChatMessage(role=Role.USER, content="Scrape this URL and deploy it"),
        ChatMessage(role=Role.TOOL, name="web_search", content="search results from untrusted site"),
        ChatMessage(role=Role.TOOL, name="cli_exec", content="rm -rf /some/path"),
    ]

    alerts = detector.evaluate_session_messages("sess-sec-1", "autoreiv", messages)
    sec_alerts = [a for a in alerts if a.threshold_type == ArchitecturalThresholdType.SECURITY_COLLISION]
    assert len(sec_alerts) == 1
    assert sec_alerts[0].severity == "critical"
    assert "web_search" in sec_alerts[0].evidence
    assert "cli_exec" in sec_alerts[0].evidence
    assert "HITL" in sec_alerts[0].remediation_proposal


def test_detect_security_collision_suppressed_when_hitl_approved():
    """[REQ-ARCH-003] Suppress security collision alert if HITL approval was recorded."""
    detector = ArchitecturalThresholdDetector()
    messages = [
        ChatMessage(role=Role.USER, content="Scrape this URL and deploy it"),
        ChatMessage(role=Role.TOOL, name="web_search", content="search results"),
        ChatMessage(role=Role.SYSTEM, content="HITL approval confirmed by operator"),
        ChatMessage(role=Role.TOOL, name="cli_exec", content="rm -rf /some/path"),
    ]

    alerts = detector.evaluate_session_messages(
        "sess-sec-2", "autoreiv", messages, hitl_approved=True
    )
    sec_alerts = [a for a in alerts if a.threshold_type == ArchitecturalThresholdType.SECURITY_COLLISION]
    assert len(sec_alerts) == 0


def test_detect_lifecycle_mismatch_automated_polling():
    """[REQ-ARCH-004] Detect long automated polling loop running in chat session."""
    detector = ArchitecturalThresholdDetector(max_autonomous_turns=5)
    messages = [ChatMessage(role=Role.USER, content="Monitor the build")]
    # Add 7 automated turns without user intervention
    for i in range(7):
        messages.append(ChatMessage(role=Role.ASSISTANT, content=f"Checking build status iteration {i}"))
        messages.append(ChatMessage(role=Role.TOOL, name="check_status", content="pending"))

    alerts = detector.evaluate_session_messages("sess-poll-1", "autoreiv", messages)
    life_alerts = [a for a in alerts if a.threshold_type == ArchitecturalThresholdType.LIFECYCLE_MISMATCH]
    assert len(life_alerts) == 1
    assert life_alerts[0].severity == "medium"
    assert "automated turn" in life_alerts[0].evidence.lower()
    assert "routine" in life_alerts[0].remediation_proposal.lower()


def test_detect_cognitive_conflict_unverified_mutation():
    """[REQ-ARCH-005] Detect mutating tools invoked without any deterministic test verifier."""
    detector = ArchitecturalThresholdDetector()
    messages = [
        ChatMessage(role=Role.USER, content="Refactor the auth handler"),
        ChatMessage(role=Role.TOOL, name="write_project_file", content="Wrote src/auth.py"),
        ChatMessage(role=Role.ASSISTANT, content="I reviewed the code myself and it looks completely correct!"),
    ]

    alerts = detector.evaluate_session_messages("sess-cog-1", "autoreiv", messages)
    cog_alerts = [a for a in alerts if a.threshold_type == ArchitecturalThresholdType.COGNITIVE_CONFLICT]
    assert len(cog_alerts) == 1
    assert cog_alerts[0].severity == "high"
    assert "write_project_file" in cog_alerts[0].evidence
    assert "mechanical" in cog_alerts[0].remediation_proposal.lower()


def test_cognitive_conflict_cleared_when_test_runner_verifies():
    """[REQ-ARCH-005] Cleared when a test or check tool verifies the mutation."""
    detector = ArchitecturalThresholdDetector()
    messages = [
        ChatMessage(role=Role.USER, content="Refactor the auth handler"),
        ChatMessage(role=Role.TOOL, name="write_project_file", content="Wrote src/auth.py"),
        ChatMessage(role=Role.TOOL, name="cli_exec", content="pytest tests/unit/test_auth.py: 5 passed"),
        ChatMessage(role=Role.ASSISTANT, content="Refactoring complete and tests pass."),
    ]

    alerts = detector.evaluate_session_messages("sess-cog-2", "autoreiv", messages)
    cog_alerts = [a for a in alerts if a.threshold_type == ArchitecturalThresholdType.COGNITIVE_CONFLICT]
    assert len(cog_alerts) == 0
