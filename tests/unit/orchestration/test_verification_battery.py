"""
Unit tests for the 4-Stage Verification Battery Pipeline [REQ-FACT-009].
"""

import pytest

from src.application.orchestration.verification_battery import VerificationBatteryService
from src.application.skills.sandbox_runner import SandboxTestRunner


@pytest.fixture
def battery_service():
    runner = SandboxTestRunner()
    return VerificationBatteryService(runner=runner)


@pytest.mark.asyncio
async def test_stage_1_functional_execution(battery_service):
    # 1. Successful functional test
    valid_tool = "def get_val(): return 42"
    valid_test = "from tool import get_val\nassert get_val() == 42"
    res = await battery_service.run_battery(valid_tool, valid_test)
    assert res.stage_1_functional is True

    # 2. Failing functional test
    broken_test = "from tool import get_val\nassert get_val() == 99"
    res_fail = await battery_service.run_battery(valid_tool, broken_test)
    assert res_fail.stage_1_functional is False
    assert res_fail.passed is False


@pytest.mark.asyncio
async def test_stage_2_safety_guardrails_blocks_path_traversal(battery_service):
    traversal_tool = """
def read_parent():
    with open("../../secrets.txt", "r") as f:
        return f.read()
"""
    test_code = "from tool import read_parent\npass"
    res = await battery_service.run_battery(traversal_tool, test_code)
    assert res.stage_2_safety is False
    assert res.passed is False
    assert "path traversal" in res.critic_notes.lower() or "safety" in res.critic_notes.lower()


@pytest.mark.asyncio
async def test_stage_3_idempotency_detects_state_crash(battery_service):
    # Tool that fails on second run because it doesn't handle existing file
    non_idempotent_tool = """
import os

def create_state_marker():
    if os.path.exists("marker.lock"):
        raise FileExistsError("Cannot run twice")
    with open("marker.lock", "w") as f:
        f.write("locked")
    return {"success": True}
"""
    test_code = """
from tool import create_state_marker
res = create_state_marker()
assert res["success"] is True
"""
    res = await battery_service.run_battery(non_idempotent_tool, test_code)
    assert res.stage_1_functional is True
    assert res.stage_3_idempotency is False
    assert res.passed is False


@pytest.mark.asyncio
async def test_stage_4_critic_ast_audit_flags_dangerous_patterns(battery_service):
    dangerous_tool = """
def execute_dynamic(user_input: str) -> dict:
    result = eval(user_input)
    return {"success": True, "result": result}
"""
    test_code = "from tool import execute_dynamic\npass"
    res = await battery_service.run_battery(dangerous_tool, test_code)
    assert res.stage_4_critic is False
    assert res.passed is False
    assert "eval" in res.critic_notes.lower()


@pytest.mark.asyncio
async def test_complete_4_stage_battery_all_pass(battery_service):
    gold_tool = """
from typing import Dict, Any

def inspect_server(name: str = "default") -> Dict[str, Any]:
    try:
        if not name:
            return {"success": False, "error": "Name required"}
        return {"success": True, "server_name": name, "status": "active"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
"""
    gold_test = """
from tool import inspect_server

# 1. Normal run
res = inspect_server("palworld")
assert res["success"] is True
assert res["status"] == "active"

# 2. Edge case
res_empty = inspect_server("")
assert res_empty["success"] is False
"""
    res = await battery_service.run_battery(gold_tool, gold_test)
    assert res.stage_1_functional is True
    assert res.stage_2_safety is True
    assert res.stage_3_idempotency is True
    assert res.stage_4_critic is True
    assert res.passed is True
    assert len(res.checks_executed) == 4


@pytest.mark.asyncio
async def test_battery_flags_environment_command_collision(battery_service):
    # Tool that simulates an intercepted cmdlet error in stderr
    collision_tool = """
import sys

def manage_mock(action: str = "status", **kwargs):
    sys.stderr.write("Get-VM : You are not currently connected to any servers. ViServerConnectionException\\n")
    return {"success": False, "error": "collision"}
"""
    test_code = """
from tool import manage_mock
res = manage_mock(action="status")
"""
    res = await battery_service.run_battery(collision_tool, test_code)
    assert res.passed is False
    assert res.stage_2_safety is False
    assert "collision" in res.critic_notes.lower()


def test_is_shallow_stub_artifact_accepts_overview_heading():
    from src.application.orchestration.verification_battery import is_shallow_stub_artifact

    skill_md = """---
name: manage-opentofu-hyperv
description: Manage OpenTofu infrastructure.
tools:
  - manage_homelab_admin
---

# Homelab Admin Runbook

## Overview
Runbook for managing OpenTofu and Ansible automation in the homelab environment.

### Objectives
- Deploy virtual machines
- Verify network connectivity

## Tools
- Required Capabilities: `manage_homelab_admin`

## Order
1. Run preflight checks.
2. Apply blueprints.

## Pitfalls
- Verify credentials before running.

## Done-when
- Resources deployed successfully.
"""
    # Should accept ## Overview and NOT treat as shallow stub
    assert is_shallow_stub_artifact(
        skill_md,
        tool_code="def manage_homelab_admin(): pass",
        seed_intent="Deploy opentofu and ansible infrastructure",
        objectives=["Deploy virtual machines"],
    ) is False


def test_is_shallow_stub_artifact_accepts_synthesizer_generic_skill():
    from src.application.orchestration.tool_synthesizer import ToolSynthesizer
    from src.application.orchestration.verification_battery import is_shallow_stub_artifact

    files = ToolSynthesizer.synthesize_tool(
        agent_id="homelab-admin",
        seed_intent="Learn to use the tooling and capabilities to spin up homelab blueprints",
        objectives=["Deploy blueprints", "Check health"],
        tool_name="manage_homelab_admin",
        skill_id="manage-homelab-admin",
    )
    skill_md = files.get("skills/manage-homelab-admin/SKILL.md")
    tool_code = files.get("tools/manage_homelab_admin.py")
    assert skill_md is not None

    # The synthesized generic skill must NOT be rejected by the shallow stub gate
    assert is_shallow_stub_artifact(
        skill_md,
        tool_code=tool_code,
        seed_intent="Learn to use the tooling and capabilities to spin up homelab blueprints",
        objectives=["Deploy blueprints", "Check health"],
    ) is False


