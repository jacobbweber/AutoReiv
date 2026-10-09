"""CARD-672: per-test hang watchdog (stdlib faulthandler, no extra dependency).

A test that runs longer than AUTOREIV_TEST_HANG_SECONDS (default 900 s) dumps every thread's stack and ends its
process, so the full suite / release preflight fails with a traceback instead of hanging at ~99% forever.
Under pytest-xdist only that worker ends; xdist reports it as crashed on the stuck test and carries on.
Set AUTOREIV_TEST_HANG_SECONDS=0 to turn it off. pytest's own ``faulthandler_timeout`` (same single timer)
wins when it is set.
"""

from __future__ import annotations

import faulthandler
import os
import sys

import pytest

HANG_SECONDS_ENV = "AUTOREIV_TEST_HANG_SECONDS"
DEFAULT_HANG_SECONDS = 900.0

_stderr_fd: int | None = None


def hang_seconds(config: pytest.Config) -> float:
    raw = (os.environ.get(HANG_SECONDS_ENV) or "").strip()
    try:
        seconds = float(raw) if raw else DEFAULT_HANG_SECONDS
    except ValueError:
        seconds = DEFAULT_HANG_SECONDS
    if seconds <= 0:
        return 0.0
    try:
        if float(config.getini("faulthandler_timeout") or 0) > 0:
            return 0.0
    except (TypeError, ValueError):
        pass
    return seconds


def pytest_configure(config: pytest.Config) -> None:
    global _stderr_fd
    if _stderr_fd is None:
        try:
            _stderr_fd = os.dup(sys.stderr.fileno())
        except (AttributeError, OSError, ValueError):
            _stderr_fd = os.dup(sys.__stderr__.fileno())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem):
    seconds = hang_seconds(item.config)
    armed = bool(seconds) and _stderr_fd is not None
    if armed:
        faulthandler.dump_traceback_later(seconds, exit=True, file=_stderr_fd)
    try:
        yield
    finally:
        if armed:
            faulthandler.cancel_dump_traceback_later()
