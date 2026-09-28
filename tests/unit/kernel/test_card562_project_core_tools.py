"""CARD-562: Developer's per-turn tool set keeps the project core tools (round 4 lost read_project_file)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.agent_packs.allowed_tools import resolve_allowed_tools
from src.application.kernel.agent_kernel import MAX_ACTIVE_TOOLS_PER_TURN, PROJECT_CORE_TOOLS, AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from tests.unit.agent_packs.catalog import platform_pack_profile


@pytest.fixture
def kernel_and_dev(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(tmp_path / "ops.db"))
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path / "data"))
    dev = platform_pack_profile("developer")
    reg = ScopedToolRegistry()
    extra = {"wiki_note_read", "get_weather", "web_search", "cli_exec", "execute_code"}  # not allowed: never mounted
    for name in sorted(resolve_allowed_tools(dev).names | extra):
        reg.register_tool(name, f"{name.replace('_', ' ')} tool", {"type": "object", "properties": {}}, lambda **kw: "ok")
    store = MagicMock()
    store.get_setting.return_value = None
    return AgentKernel(gateway=MagicMock(), tool_registry=reg, state_store=store, telemetry=MagicMock()), dev


def test_allowed_set_is_bigger_than_the_turn_cap(kernel_and_dev):
    _, dev = kernel_and_dev
    assert len(resolve_allowed_tools(dev).names) > MAX_ACTIVE_TOOLS_PER_TURN


@pytest.mark.parametrize(
    "text", ["Work card CARD-1 in the active project and stop when it is In Review.", "hello", "commit and branch"]
)
def test_project_core_tools_always_mounted(kernel_and_dev, text):
    kernel, dev = kernel_and_dev
    names = [t.name for t in kernel._resolve_active_tools(dev, user_content=text)]
    assert len(names) <= MAX_ACTIVE_TOOLS_PER_TURN
    assert PROJECT_CORE_TOOLS <= set(names), set(PROJECT_CORE_TOOLS) - set(names)
    assert not {"cli_exec", "execute_code", "get_weather"} & set(names)


def test_selected_skill_tools_come_with_the_core(kernel_and_dev):
    kernel, dev = kernel_and_dev
    names = set(t.name for t in kernel._resolve_active_tools(dev, user_content="x", active_skills=["git-workflow"]))
    assert {"git_create_branch", "git_commit", "git_status", "git_diff"} <= names
    assert PROJECT_CORE_TOOLS <= names
    assert len(names) <= MAX_ACTIVE_TOOLS_PER_TURN
