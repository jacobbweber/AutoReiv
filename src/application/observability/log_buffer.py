"""
Thread-safe circular in-memory system log buffer and logging handler [REQ-OBS-005].
"""

from __future__ import annotations

import collections
import datetime
import logging
import threading
from typing import Any, Dict, List, Optional


class LogEntry:
    """Represents a structured runtime log event."""

    def __init__(
        self,
        timestamp: str,
        level: str,
        message: str,
        logger_name: str = "autoreiv",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.timestamp = timestamp
        self.level = level.upper()
        self.message = message
        self.logger_name = logger_name
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "logger": self.logger_name,
            "metadata": self.metadata,
        }


class SystemLogBuffer:
    """
    In-memory thread-safe circular ring buffer for runtime logs and telemetry events.
    """

    _instance: Optional[SystemLogBuffer] = None
    _lock = threading.Lock()

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._buffer: collections.deque[LogEntry] = collections.deque(maxlen=capacity)
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls, capacity: int = 1000) -> SystemLogBuffer:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(capacity=capacity)
        return cls._instance

    def add_entry(
        self,
        level: str,
        message: str,
        logger_name: str = "autoreiv",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        entry = LogEntry(
            timestamp=now_str,
            level=level,
            message=message,
            logger_name=logger_name,
            metadata=metadata,
        )
        with self._lock:
            self._buffer.append(entry)
        return entry

    def get_logs(
        self,
        limit: int = 100,
        level: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            entries = list(self._buffer)

        if level and level.upper() != "ALL":
            target_lvl = level.upper()
            entries = [e for e in entries if e.level == target_lvl]

        if query:
            q = query.lower()
            entries = [e for e in entries if q in e.message.lower() or q in e.logger_name.lower()]

        # Return latest entries up to limit
        return [e.to_dict() for e in entries[-limit:]]

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


class MemoryLogHandler(logging.Handler):
    """
    Standard logging Handler directing log records into SystemLogBuffer.
    """

    def __init__(self, buffer: SystemLogBuffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.buffer.add_entry(
                level=record.levelname,
                message=msg,
                logger_name=record.name,
            )
        except Exception:
            self.handleError(record)


def setup_system_logging(buffer: Optional[SystemLogBuffer] = None) -> SystemLogBuffer:
    """Attach the MemoryLogHandler to root and uvicorn loggers."""
    buf = buffer or SystemLogBuffer.get_instance()
    handler = MemoryLogHandler(buf)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

    # Cleanly replace any existing MemoryLogHandlers
    root_logger.handlers = [h for h in root_logger.handlers if not isinstance(h, MemoryLogHandler)]
    root_logger.addHandler(handler)

    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.handlers = [h for h in uvicorn_logger.handlers if not isinstance(h, MemoryLogHandler)]
    uvicorn_logger.addHandler(handler)

    return buf
