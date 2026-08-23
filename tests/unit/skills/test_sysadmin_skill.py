"""
Unit tests for Sysadmin Skill (System Info & Safe CLI) [REQ-AGENTS-003, REQ-AGENTS-004].
"""

import sys

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.sysadmin_skill import SysadminSkill
from src.domain.agents.profiles import LINUX_SYSADMIN_PROFILE
from src.domain.gateway.models import ToolCall


@pytest.fixture
def skill():
    return SysadminSkill()


def test_get_system_info_returns_valid_metrics(skill):
    info = skill.get_system_info()
    assert "os_name" in info
    assert "cpu_count" in info
    assert info["cpu_count"] >= 1
    assert "memory_total_gb" in info
    assert info["memory_total_gb"] > 0
    assert "disk_total_gb" in info
    assert "uptime_seconds" in info


@pytest.mark.asyncio
async def test_run_cli_command_echo(skill):
    cmd = "echo Hello AutoReiv"
    res = await skill.run_cli_command(command=cmd)
    assert res["exit_code"] == 0
    assert "Hello AutoReiv" in res["stdout"]
    assert res["duration_ms"] > 0


@pytest.mark.asyncio
async def test_run_cli_command_timeout(skill):
    # Sleep longer than timeout
    if sys.platform == "win32":
        cmd = "powershell -Command Start-Sleep -Seconds 3"
    else:
        cmd = "sleep 3"

    res = await skill.run_cli_command(command=cmd, timeout_seconds=0.2)
    assert res["exit_code"] == -1
    assert "timed out" in res["stderr"].lower() or "timed out" in str(res.get("error", "")).lower()


@pytest.mark.asyncio
async def test_sysadmin_registered_tool_execution(skill):
    registry = ScopedToolRegistry()
    skill.register_tools(registry)

    # Linux Sysadmin is authorized for system_info
    call = ToolCall(id="call_sys", name="system_info", arguments={})
    res = await registry.execute(call, LINUX_SYSADMIN_PROFILE)

    assert res.success is True
    assert "cpu_count" in res.output
    assert "memory_total_gb" in res.output
