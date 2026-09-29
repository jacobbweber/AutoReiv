"""CARD-562: prompt text never names tools the agent may not call; disallowed calls are refused where enforced."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from src.application.agent_skills.allowed_tools import resolve_allowed_tools
from src.application.kernel.agent_kernel import project_tool_guidance
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import platform_pack_profile

pytestmark = pytest.mark.guard

RUNNERS = ("cli_exec", "execute_code")
_TOOLISH = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")


def _developer_allowed() -> set[str]:
    return set(resolve_allowed_tools(platform_pack_profile("developer")).names)


def test_developer_project_guidance_names_only_allowed_tools():
    allowed = _developer_allowed()
    text = project_tool_guidance(allowed)
    assert "run_project_checks" in text
    for runner in RUNNERS:
        assert runner not in text
    named = set(_TOOLISH.findall(text))
    assert named, text
    assert named <= allowed, named - allowed


@pytest.mark.parametrize("allowed", [set(), {"read_project_file"}, {"cli_exec", "list_project_dir"}, {"run_project_checks"}])
def test_guidance_is_a_subset_of_whatever_is_allowed(allowed):
    assert set(_TOOLISH.findall(project_tool_guidance(allowed))) <= allowed


def test_kernel_has_no_hardcoded_cli_exec_advice_outside_the_guard():
    src = Path("src/application/kernel/agent_kernel.py").read_text(encoding="utf-8")
    assert src.count("Use cli_exec") == 1  # only inside project_tool_guidance, behind `"cli_exec" in allowed_tools`


@pytest.mark.parametrize("runner", RUNNERS)
def test_gate_refuses_runner_for_developer(runner):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    d = ToolPolicyGate(store=store).evaluate(
        ToolCall(id="c1", name=runner, arguments={"command": "node --test"}),
        platform_pack_profile("developer"),
        registry_tool_names={runner, "run_project_checks"},
    )
    assert d.verdict == ToolPolicyVerdict.BLOCK
    assert d.policy_source == "agent_allowlist"


@pytest.mark.parametrize("runner", RUNNERS)
def test_registry_refuses_runner_for_developer(runner, tmp_path):
    from src.application.telemetry.collector import TelemetryCollector
    from src.infrastructure.agents.registry import BuiltinAgentRegistry

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store, telemetry=TelemetryCollector(store=store), skills_dir=str(tmp_path / "skills")
    )
    dev = agent_reg.get_profile("developer")
    result = asyncio.run(tool_reg.execute(ToolCall(id="c2", name=runner, arguments={"command": "echo hi"}), dev))
    assert result.success is False
    assert "not authorized" in (result.error or "")
