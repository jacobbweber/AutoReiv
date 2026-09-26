"""CARD-511: NativeCustomToolService runs the tool check before it saves anything (tests 13-16)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.native_tool_engineering import NativeToolEngineeringTools
from src.application.tools.native_packaging import (
    NativeCustomToolService,
    NativeToolCheckFailed,
    NativeToolError,
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
        "grant_agent_ids": ["autoreiv"],
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
    assert store.get_setting("native_custom_tools") in (None, [])
    assert "c511_broken" not in registry
    assert store.get_agent_override("autoreiv") is None
    assert store.get_setting("tool_policy") == policy_before


async def test_14_good_tool_row_carries_the_check(env):
    store, registry, service = env
    body = await service.register(_raw("c511_good", GOOD))
    assert body["success"] is True
    assert body["persisted"] is True
    assert body["mounted"] is True
    assert body["granted_agent_ids"] == ["autoreiv"]
    assert body["check"]["status"] == "passed"
    assert body["message"].startswith("Checked: c511_good")
    row = store.get_setting("native_custom_tools")[0]
    assert row["check"]["status"] == "passed"
    assert row["check"]["sample_arguments"] == {}
    assert service.list_tools()[0]["check"]["status"] == "passed"
    assert "c511_good" in registry


async def test_14b_high_risk_registers_checked_without_call(env):
    store, _registry, service = env
    body = await service.register(_raw("c511_high", GOOD, risk_level="high", grant_agent_ids=[]))
    assert body["requires_hitl"] is True
    assert body["check"]["status"] == "checked_without_call"
    assert body["check"]["skip_reason"] == "high risk: sample call skipped"


async def test_14c_skip_needs_a_reason(env):
    _store, _registry, service = env
    with pytest.raises(NativeToolError) as caught:
        await service.register(_raw("c511_skip", GOOD, sample_call="skip"))
    assert caught.value.status_code == 400
    assert "skip_reason" in str(caught.value)
    body = await service.register(_raw("c511_skip", GOOD, sample_call="skip", skip_reason="sends email", grant_agent_ids=[]))
    assert body["check"]["status"] == "checked_without_call"
    assert body["check"]["skip_reason"] == "sends email"


async def test_15_old_row_without_check_still_mounts(env):
    store, registry, service = env
    store.set_setting(
        "native_custom_tools",
        [{"name": "c511_old", "description": "old", "code": GOOD, "parameters": {}, "requires_hitl": False, "risk_level": "low"}],
    )
    assert "c511_old" in service.mount_persisted()
    assert "c511_old" in registry
    assert service.list_tools()[0]["check"] is None


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
