"""CARD-519: agent credentials stay in the calling task's tool context, never in os.environ; a native tool's
subprocess gets only its own agent's credentials."""

from __future__ import annotations

import asyncio
import os

import pytest

from src.application.kernel.tool_registry import (
    ScopedToolRegistry,
    credential_env_from_context,
    credential_env_key,
    get_tool_context,
)
from src.application.skills.sandbox_worker import SandboxedSubprocessWorker
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile
from src.domain.security.vault import Credential
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

pytestmark = pytest.mark.guard


def _agent(aid, creds):
    return AgentProfile(id=aid, name=aid, description=aid, system_prompt="x", allowed_skill=["tool:probe"],
                        allowed_credentials=creds)


@pytest.mark.asyncio
async def test_two_concurrent_calls_never_see_each_others_secret(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    store.initialize_db()
    store.save_credential(Credential(id="alpha-key", name="a", type="token", secret="secret-alpha-111"))
    store.save_credential(Credential(id="beta-key", name="b", type="token", secret="secret-beta-222"))
    registry = ScopedToolRegistry(state_store=store)
    seen = {}
    both_inside = asyncio.Event()
    inside = []

    async def probe():
        me = get_tool_context()["agent_id"]
        inside.append(me)
        if len(inside) == 2:
            both_inside.set()
        await asyncio.wait_for(both_inside.wait(), 5)  # both calls are running at the same time
        env_creds = {k: v for k, v in os.environ.items() if k.startswith("AUTOREIV_CRED_")}
        seen[me] = {"env": env_creds, "ctx": dict(get_tool_context()["credentials"]),
                    "sub": credential_env_from_context(),
                    "sandbox_env": {k: v for k, v in SandboxedSubprocessWorker.sanitize_environment(
                        credential_env_from_context()).items() if k.startswith("AUTOREIV_CRED_")}}
        return "ok"

    registry.register_tool(name="probe", description="p", parameters={"type": "object", "properties": {}}, handler=probe)
    a, b = await asyncio.gather(
        registry.execute(ToolCall(id="1", name="probe", arguments={}), _agent("alpha", ["alpha-key"])),
        registry.execute(ToolCall(id="2", name="probe", arguments={}), _agent("beta", ["beta-key"])),
    )
    assert a.success and b.success
    assert seen["alpha"]["env"] == {} and seen["beta"]["env"] == {}
    assert seen["alpha"]["ctx"] == {"alpha-key": "secret-alpha-111"}
    assert seen["beta"]["ctx"] == {"beta-key": "secret-beta-222"}
    assert seen["alpha"]["sandbox_env"] == {"AUTOREIV_CRED_ALPHA_KEY": "secret-alpha-111"}
    assert seen["beta"]["sandbox_env"] == {"AUTOREIV_CRED_BETA_KEY": "secret-beta-222"}


def test_sanitizer_drops_host_credential_vars(monkeypatch):
    monkeypatch.setenv("AUTOREIV_CRED_OTHER", "leak")
    env = SandboxedSubprocessWorker.sanitize_environment({"AUTOREIV_CRED_MINE": "mine"})
    assert "AUTOREIV_CRED_OTHER" not in env
    assert env["AUTOREIV_CRED_MINE"] == "mine"
    assert credential_env_key("github-pat") == "AUTOREIV_CRED_GITHUB_PAT"


@pytest.mark.asyncio
async def test_native_tool_subprocess_receives_its_granted_credential(tmp_path):
    from src.application.tools import native_packaging

    store = SQLiteStateStore(db_path=str(tmp_path / "t.db"))
    store.initialize_db()
    store.save_credential(Credential(id="svc", name="s", type="token", secret="svc-secret-9"))
    registry = ScopedToolRegistry(state_store=store)
    code = "import os\ndef run(**kwargs):\n    return os.environ.get('AUTOREIV_CRED_SVC')\n"

    async def handler():
        return await native_packaging._run_sandboxed(code, {})

    registry.register_tool(name="probe", description="p", parameters={"type": "object", "properties": {}}, handler=handler)
    granted = await registry.execute(ToolCall(id="1", name="probe", arguments={}), _agent("a", ["svc"]))
    denied = await registry.execute(ToolCall(id="2", name="probe", arguments={}), _agent("b", []))
    assert granted.success, granted.error
    assert "svc-secret-9" in str(granted.output)
    assert "svc-secret-9" not in str(denied.output)
