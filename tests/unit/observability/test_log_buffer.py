"""
Unit tests for SystemLogBuffer and in-memory logging [REQ-OBS-005].
"""

import logging

from src.application.observability.log_buffer import SystemLogBuffer, setup_system_logging


def test_system_log_buffer_add_and_filter():
    buf = SystemLogBuffer(capacity=10)
    buf.add_entry(level="INFO", message="Server started", logger_name="web")
    buf.add_entry(level="WARN", message="High memory usage", logger_name="system")
    buf.add_entry(level="ERROR", message="Gateway timeout: 192.168.1.29", logger_name="gateway")

    # Get all logs
    logs = buf.get_logs(limit=10)
    assert len(logs) == 3
    assert logs[0]["message"] == "Server started"
    assert logs[2]["level"] == "ERROR"

    # Filter by level
    err_logs = buf.get_logs(level="ERROR")
    assert len(err_logs) == 1
    assert err_logs[0]["message"] == "Gateway timeout: 192.168.1.29"

    # Filter by query
    gw_logs = buf.get_logs(query="timeout")
    assert len(gw_logs) == 1
    assert "timeout" in gw_logs[0]["message"]


def test_system_log_buffer_capacity():
    buf = SystemLogBuffer(capacity=3)
    for i in range(5):
        buf.add_entry(level="INFO", message=f"Log msg {i}")

    logs = buf.get_logs()
    assert len(logs) == 3
    assert logs[0]["message"] == "Log msg 2"
    assert logs[2]["message"] == "Log msg 4"


def test_logging_integration():
    buf = SystemLogBuffer(capacity=50)
    setup_system_logging(buf)

    test_logger = logging.getLogger("test_autoreiv")
    test_logger.info("Test logging integration entry")

    logs = buf.get_logs(query="Test logging integration entry")
    assert len(logs) >= 1
    assert logs[-1]["level"] == "INFO"
