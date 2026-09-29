"""CARD-511: NativeCustomToolService runs the tool check before it saves anything (tests 13-16)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.native_tool_engineering import NativeToolEngineeringTools
from src.application.tools.native_packaging import (
    NativeCustomToolService,
    NativeToolCheckFailed,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

GOOD = "def run(text='', **kw):\n    return {'echo': text}\n"
BROKEN = "import nonexistent_c511_mod\n\ndef run(**kw):\n    return 1\n"
SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}}}


class _Agents:
    def __init__(self):
        self.profile = SimpleNamespace(id="autoreiv", allowed_tool_names=["recall_agent_memory"])

    def get_agent(self, agent_id):
        return self.profile if agent_id == "autoreiv" else None


@pytest.fixture
def env(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "s.db"))
    store.initialize_db()
    registry = ScopedToolRegistry()
    service = NativeCustomToolService(store=store, tool_registry=registry, agent_registry=_Agents())
    return store, registry, service


def _raw(name, code, **extra):
    body = {
        "name": name,
        "description": f"CARD-511 {name}",
        "code": code,
        "parameters": SCHEMA,
        "requires_hitl": False,
        "risk_level": "low",
        "target_agent_id": "autoreiv",
    }
    body.update(extra)
    return body


async def test_13_broken_tool_saves_mounts_grants_and_syncs_nothing(env):
    store, registry, service = env
    policy_before = store.get_setting("tool_policy")
    with pytest.raises(NativeToolCheckFailed) as caught:
        await service.register(_raw("c511_broken", BROKEN))
    assert caught.value.status_code == 422
    assert caught.value.check["status"] == "failed"
    assert caught.value.check["stage"] == "import"
    assert str(caught.value).startswith("Not registered: c511_broken failed the import check")
    assert service.list_tools() == []
    assert "c511_broken" not in registry
    assert store.get_pending_approvals(agent_id="autoreiv") == []
    assert store.get_setting("tool_policy") == policy_before


async def test_14_good_tool_row_carries_the_check(env):
    store, registry, service = env
    body = await service.register(_raw("c511_good", GOOD))
    assert body["success"] is True
    assert body["persisted"] is True
    assert body["mounted"] is False  # CARD-570: saved, not mounted until Jacob enables it
    assert body["approval"] == "disabled"
    assert body["proposal"]["status"] == "pending" and body["proposal"]["agent_id"] == "autoreiv"  # CARD-539
    assert body["check"]["status"] == "passed"
    assert body["message"].startswith("Checked: c511_good")
    assert "Jacob must enable it" in body["message"]
    row = service.get("c511_good")
    assert row["check"]["status"] == "passed"
    assert row["check"]["sample_arguments"] == {}
    assert service.list_tools()[0]["check"]["status"] == "passed"
    assert "c511_good" not in registry
    assert service.enable_by_operator("c511_good")["mounted"] is True
    assert "c511_good" in registry


async def test_14b_high_risk_registers_checked_without_call(env):
    store, _registry, service = env
    body = await service.register(_raw("c511_high", GOOD, risk_level="high", target_agent_id=""))
    assert body["requires_hitl"] is True
    assert body["check"]["status"] == "checked_without_call"
    assert body["check"]["skip_reason"] == "high risk: sample call skipped"


class _CountingRunner:
    def __init__(self):
        self.calls = 0

    async def __call__(self, args, **kwargs):
        self.calls += 1
        raise AssertionError("the sandbox runner must not be called for flagged code")


async def test_14c_skip_flag_is_ignored_pure_code_still_runs(env):
    """CARD-571: a model-passed skip flag has no effect; pure code gets its trial run."""
    _store, _registry, service = env
    body = await service.register(_raw("c511_skip", GOOD, sample_call="skip", skip_reason="sends email", target_agent_id=""))
    assert body["check"]["status"] == "passed"
    assert body["check"]["skip_reason"] is None


@pytest.mark.parametrize(
    "code, access",
    [
        ("import urllib.request\n\ndef run(**kw):\n    return 1\n", "network"),
        ("def run(**kw):\n    return open('x.txt').read()\n", "files"),
        ("import subprocess\n\ndef run(**kw):\n    return 1\n", "programs"),
        ("def run(**kw):\n    return __import__('os').getcwd()\n", "hidden_imports"),
    ],
)
async def test_14d_saving_flagged_code_never_invokes_the_sandbox_runner(env, code, access):
    """CARD-571 guard: flagged code is saved as Not run, whatever the caller passes."""
    from src.application.tools.tool_check import ToolCheckService

    _store, _registry, service = env
    runner = _CountingRunner()
    service.checker = ToolCheckService(runner=runner)
    body = await service.register(_raw("c571_flag", code, sample_call="run", target_agent_id=""))
    assert runner.calls == 0
    assert body["check"]["status"] == "not_run_review"
    assert access in body["check"]["access"]
    assert "Not run: uses" in body["message"] and "review before enabling" in body["message"]
    assert body["approval"] != "enabled"


async def test_15_only_enabled_approved_tools_remount(env):
    """CARD-570: startup mounts a tool file only when Jacob enabled it and the code hash still matches."""
    _store, registry, service = env
    await service.register(_raw("c511_old", GOOD, target_agent_id=""))
    assert service.mount_persisted() == []
    service.enable_by_operator("c511_old")
    registry.unmount_tool("c511_old")
    assert "c511_old" in service.mount_persisted()
    assert "c511_old" in registry


async def test_16_chat_tool_returns_not_registered(env):
    store, registry, service = env
    tools = NativeToolEngineeringTools(state_store=store, tool_registry=registry)
    tools.service = service
    result = await tools.register_native_tool(name="c511_chat", description="broken via chat", code=BROKEN)
    assert result["success"] is False
    assert result["registered"] is False
    assert result["message"].startswith("Not registered: c511_chat failed the import check")
    assert result["check"]["stage"] == "import"
    assert "c511_chat" not in registry
