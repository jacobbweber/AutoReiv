"""
Unit tests for DangerousCommandFilter and SandboxedSubprocessWorker [REQ-SAFE-001, REQ-SAFE-002].
"""

import pytest

from src.application.skills.command_filter import DangerousCommandFilter
from src.application.skills.sandbox_worker import SandboxedSubprocessWorker


def test_dangerous_command_filter_detects_prohibited_patterns():
    prohibited = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda",
        ":(){ :|:& };:",
        "format c: /fs:NTFS",
        "DROP DATABASE production;",
        "DROP TABLE users;",
    ]
    for cmd in prohibited:
        is_dan, reason = DangerousCommandFilter.is_dangerous(cmd)
        assert is_dan is True
        assert reason is not None


def test_dangerous_command_filter_allows_safe_commands():
    safe_commands = [
        "ls -la",
        "git status",
        "pytest tests/",
        "cat README.md",
        "echo 'Hello World'",
        "python -m pip list",
    ]
    for cmd in safe_commands:
        is_dan, reason = DangerousCommandFilter.is_dangerous(cmd)
        assert is_dan is False
        assert reason is None


@pytest.mark.asyncio
async def test_sandboxed_subprocess_worker_runs_in_temp_dir():
    # Python script printing cwd and writing a scratch file
    code = 'import os; print("CWD:" + os.getcwd()); open("test.txt", "w").write("ok")'
    result = await SandboxedSubprocessWorker.run_python_code(code, timeout_seconds=5.0)

    assert result.success is True
    assert "CWD:" in result.stdout
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_sandboxed_subprocess_worker_enforces_timeout():
    code = "import time; time.sleep(10)"
    result = await SandboxedSubprocessWorker.run_python_code(code, timeout_seconds=0.5)

    assert result.success is False
    assert "timed out" in (result.error or "").lower()
