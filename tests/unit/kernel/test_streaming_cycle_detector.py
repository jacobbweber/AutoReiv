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
