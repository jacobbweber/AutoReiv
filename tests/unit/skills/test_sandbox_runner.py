"""
Unit and integration tests for Isolated Sandbox Mock Environment & Test Runner [REQ-FACT-008].
"""

import pytest

from src.application.skills.sandbox_runner import SandboxTestRunner


@pytest.mark.asyncio
async def test_sandbox_runner_executes_valid_tool_test():
    runner = SandboxTestRunner()
    tool_code = """
def get_server_status() -> dict:
    return {"status": "online", "players": 4, "server_name": "TestWorld"}
"""
    test_code = """
from tool import get_server_status

res = get_server_status()
assert res["status"] == "online"
assert res["players"] == 4
print("ALL_TESTS_PASS")
"""
    result = await runner.run_tool_test(
        tool_code=tool_code,
        test_code=test_code,
        timeout_seconds=10.0,
    )

    assert result.exit_code == 0
    assert result.success is True
    assert "ALL_TESTS_PASS" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_runner_captures_failure_and_traceback():
    runner = SandboxTestRunner()
    tool_code = """
def add(a, b):
    return a + b
"""
    test_code = """
from tool import add
assert add(2, 2) == 5, "Math invariant violated"
"""
    result = await runner.run_tool_test(
        tool_code=tool_code,
        test_code=test_code,
        timeout_seconds=5.0,
    )

    assert result.exit_code != 0
    assert result.success is False
    assert "AssertionError: Math invariant violated" in result.stderr or "AssertionError" in result.stderr


@pytest.mark.asyncio
async def test_sandbox_runner_mirrors_directory(tmp_path):
    # Setup host mock directory
    host_dir = tmp_path / "host_server"
    host_dir.mkdir()
    config_dir = host_dir / "Config"
    config_dir.mkdir()
    (config_dir / "settings.ini").write_text("[Game]\nDifficulty=Normal\n", encoding="utf-8")

    runner = SandboxTestRunner()
    tool_code = """
from pathlib import Path

def read_game_difficulty() -> str:
    path = Path("Config/settings.ini")
    if not path.is_file():
        raise FileNotFoundError("Config missing")
    content = path.read_text(encoding="utf-8")
    for line in content.splitlines():
        if line.startswith("Difficulty="):
            return line.split("=", 1)[1].strip()
    return "Unknown"
"""
    test_code = """
from tool import read_game_difficulty

diff = read_game_difficulty()
assert diff == "Normal", f"Expected Normal, got {diff}"
print(f"DIFFICULTY_IS_{diff}")
"""
    result = await runner.run_tool_test(
        tool_code=tool_code,
        test_code=test_code,
        mirror_dir=str(host_dir),
        timeout_seconds=5.0,
    )

    assert result.exit_code == 0
    assert result.success is True
    assert "DIFFICULTY_IS_Normal" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_runner_scrubs_host_secrets(monkeypatch):
    monkeypatch.setenv("PALWORLD_ADMIN_PASSWORD", "super_secret_shhh")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "token_12345")

    runner = SandboxTestRunner()
    tool_code = """
import os

def check_leaks() -> dict:
    return {
        "admin_password": os.environ.get("PALWORLD_ADMIN_PASSWORD"),
        "bot_token": os.environ.get("DISCORD_BOT_TOKEN"),
    }
"""
    test_code = """
from tool import check_leaks

leaks = check_leaks()
assert leaks["admin_password"] is None, f"Admin password leaked: {leaks['admin_password']}"
assert leaks["bot_token"] is None, f"Bot token leaked: {leaks['bot_token']}"
print("ENVIRONMENT_CLEAN")
"""
    result = await runner.run_tool_test(
        tool_code=tool_code,
        test_code=test_code,
        timeout_seconds=5.0,
    )

    assert result.exit_code == 0
    assert result.success is True
    assert "ENVIRONMENT_CLEAN" in result.stdout


@pytest.mark.asyncio
async def test_sandbox_runner_timeout_guard():
    runner = SandboxTestRunner()
    tool_code = "def loop_forever(): pass"
    test_code = """
import time
time.sleep(5.0)
print("SHOULD_NOT_REACH")
"""
    result = await runner.run_tool_test(
        tool_code=tool_code,
        test_code=test_code,
        timeout_seconds=0.5,
    )

    assert result.exit_code != 0
    assert result.success is False
    assert "timed out" in (result.error or "").lower() or "timed out" in result.stderr.lower()
