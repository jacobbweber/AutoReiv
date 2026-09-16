"""
Unit tests for CycleDetector and Streaming TTFT/TPS Telemetry [REQ-MEMORY-006].
"""

from src.application.kernel.cycle_detector import CycleDetector
from src.domain.gateway.models import ToolCall


def test_cycle_detector_identifies_repeating_tool_calls():
    detector = CycleDetector(max_repeats=3)

    tc1 = ToolCall(id="c1", name="search_docs", arguments={"query": "sysadmin"})
    tc2 = ToolCall(id="c2", name="search_docs", arguments={"query": "sysadmin"})
    tc3 = ToolCall(id="c3", name="search_docs", arguments={"query": "sysadmin"})

    assert not detector.record_and_check([tc1])
    assert not detector.record_and_check([tc2])
    # 3rd identical call triggers cycle trap
    assert detector.record_and_check([tc3])


def test_cycle_detector_resets_on_different_tool_calls():
    detector = CycleDetector(max_repeats=3)

    tc1 = ToolCall(id="c1", name="search_docs", arguments={"query": "sysadmin"})
    tc2 = ToolCall(id="c2", name="search_docs", arguments={"query": "sysadmin"})
    tc_diff = ToolCall(id="c3", name="search_docs", arguments={"query": "librarian"})
    tc3 = ToolCall(id="c4", name="search_docs", arguments={"query": "sysadmin"})

    assert not detector.record_and_check([tc1])
    assert not detector.record_and_check([tc2])
    assert not detector.record_and_check([tc_diff])
    assert not detector.record_and_check([tc3])


def test_cycle_detector_detects_oscillation():
    """Detects alternating cycles (e.g. A -> B -> A -> B -> A -> B)."""
    detector = CycleDetector(max_repeats=3)
    tc_a = ToolCall(id="ca", name="tool_a", arguments={"x": 1})
    tc_b = ToolCall(id="cb", name="tool_b", arguments={"y": 2})

    for _ in range(2):
        assert not detector.record_and_check([tc_a])
        assert not detector.record_and_check([tc_b])

    assert not detector.record_and_check([tc_a])
    # 3rd time completing the A->B pattern triggers oscillation detector
    assert detector.record_and_check([tc_b])


def test_cycle_detector_detects_argument_churn():
    """Detects repeated calls to the same tool name with churning arguments."""
    detector = CycleDetector(max_repeats=3, max_churn_repeats=5)
    for i in range(4):
        tc = ToolCall(id=f"c{i}", name="execute_query", arguments={"query": f"SELECT {i}"})
        assert not detector.record_and_check([tc])

    # 5th consecutive call to execute_query with churning args triggers churn circuit breaker
    tc5 = ToolCall(id="c5", name="execute_query", arguments={"query": "SELECT 5"})
    assert detector.record_and_check([tc5])
