"""
CARD-724 unit tests:
1. SoftwareUpdateScheduler.tick() stops calling run_auto_update_if_due() once _defer_count >= MAX_DEFER_RETRIES_PER_DAY (48), and resets on day rollover.
2. DetachedScriptRestarter.schedule_restart() on Windows builds the detached PowerShell command with -HostAddr, -Port, and _own_data_args(windows=True).
3. setup_system_logging() attaches a StreamHandler to root_logger when none is present so src.* INFO/WARNING logs reach stderr/.autoreiv-restart-serve.log.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.application.observability.log_buffer import (
    MemoryLogHandler,
    SystemLogBuffer,
    setup_system_logging,
)
from src.application.system.serve_restarter import DetachedScriptRestarter
from src.application.system.update_scheduler import (
    MAX_DEFER_RETRIES_PER_DAY,
    SoftwareUpdateScheduler,
)


@pytest.mark.asyncio
async def test_scheduler_short_circuits_after_max_defer_retries_and_resets_next_day():
    calls = 0

    class _BusyService:
        def run_auto_update_if_due(self, *, now=None):
            nonlocal calls
            calls += 1
            return SimpleNamespace(refused=True, message="Update refused: server is busy with active turn")

    scheduler = SoftwareUpdateScheduler(_BusyService(), interval_seconds=0.01)
    day1 = datetime(2026, 10, 18, 3, 0, tzinfo=timezone.utc)

    for i in range(MAX_DEFER_RETRIES_PER_DAY):
        res = await scheduler.tick(now=day1 + timedelta(minutes=i))
        assert res is not None
        assert res.refused is True

    assert calls == MAX_DEFER_RETRIES_PER_DAY

    # Ticks beyond MAX_DEFER_RETRIES_PER_DAY on the same day must short-circuit without calling update_service
    extra = await scheduler.tick(now=day1 + timedelta(minutes=MAX_DEFER_RETRIES_PER_DAY + 1))
    assert extra is None
    assert calls == MAX_DEFER_RETRIES_PER_DAY

    # Next calendar day resets the counter and calls update_service again
    day2 = day1 + timedelta(days=1)
    res_day2 = await scheduler.tick(now=day2)
    assert res_day2 is not None
    assert calls == MAX_DEFER_RETRIES_PER_DAY + 1


def test_detached_script_restarter_windows_powershell_command(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True)
    ps1 = scripts_dir / "restart_serve.ps1"
    ps1.write_text("# mock restart_serve.ps1\n", encoding="utf-8")

    monkeypatch.setattr("src.application.system.serve_restarter.sys.platform", "win32")
    monkeypatch.setenv("AUTOREIV_DEPLOY_MODE", "git")
    monkeypatch.delenv("AUTOREIV_CONTAINER", raising=False)
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(tmp_path / "wiki"))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "autoreiv.db"))

    popen_calls = []

    def _fake_popen(cmd, **kwargs):
        popen_calls.append((cmd, kwargs))
        return SimpleNamespace(pid=9999)

    with patch("src.application.system.serve_restarter.subprocess.Popen", side_effect=_fake_popen):
        restarter = DetachedScriptRestarter()
        ok = restarter.schedule_restart(host="127.0.0.1", port=8000, repo_root=tmp_path)

    assert ok is True
    assert len(popen_calls) == 1
    cmd, kwargs = popen_calls[0]
    assert cmd[:6] == [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps1),
    ]
    assert "-HostAddr" in cmd and cmd[cmd.index("-HostAddr") + 1] == "127.0.0.1"
    assert "-Port" in cmd and cmd[cmd.index("-Port") + 1] == "8000"
    assert "-DataDir" in cmd and cmd[cmd.index("-DataDir") + 1] == str(tmp_path / "data")
    assert "-WikiPath" in cmd and cmd[cmd.index("-WikiPath") + 1] == str(tmp_path / "wiki")
    assert "-DbPath" in cmd and cmd[cmd.index("-DbPath") + 1] == str(tmp_path / "autoreiv.db")
    assert kwargs.get("cwd") == str(tmp_path)
    assert kwargs.get("creationflags", 0) != 0


def test_setup_system_logging_attaches_stream_handler_for_src_logs():
    root_logger = logging.getLogger()
    saved_handlers = list(root_logger.handlers)
    saved_level = root_logger.level
    try:
        # Simulate uvicorn factory startup where root_logger has no StreamHandler
        root_logger.handlers = []
        buf = SystemLogBuffer(capacity=50)
        setup_system_logging(buf)

        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, MemoryLogHandler)
        ]
        assert len(stream_handlers) >= 1, "Expected setup_system_logging to attach a StreamHandler to root_logger"

        capture = io.StringIO()
        stream_handlers[0].setStream(capture)

        src_logger = logging.getLogger("src.application.system.update_scheduler")
        src_logger.info("CARD-724 info log line")
        src_logger.warning("CARD-724 warning log line")

        output = capture.getvalue()
        assert "CARD-724 info log line" in output
        assert "CARD-724 warning log line" in output

        buffered = [entry["message"] for entry in buf.get_logs(limit=10)]
        assert any("CARD-724 info log line" in m for m in buffered)
        assert any("CARD-724 warning log line" in m for m in buffered)
    finally:
        root_logger.handlers = saved_handlers
        root_logger.setLevel(saved_level)
