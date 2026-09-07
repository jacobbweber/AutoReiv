"""
Unit and integration tests for Credential Vault JIT injection and execution scrubbing [CARD-168].
"""

import os

import pytest

from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile
from src.domain.security.vault import Credential
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.mark.asyncio
async def test_tool_context_jit_credential_injection(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    store.initialize_db()

    cred = Credential(
        id="github-pat",
        name="GitHub PAT",
        type="token",
        secret="ghp_live_secret_token_abcdef123456",
    )
    store.save_credential(cred)

    registry = ScopedToolRegistry(state_store=store)

    context_seen = {}
    env_seen = {}

    def dummy_tool():
        ctx = get_tool_context()
        context_seen.update(ctx)
        env_seen["AUTOREIV_CRED_GITHUB_PAT"] = os.environ.get("AUTOREIV_CRED_GITHUB_PAT")
        return {"status": "ok"}

    registry.register_tool(
        name="dummy_tool",
        description="A dummy test tool",
        parameters={"type": "object", "properties": {}},
        handler=dummy_tool,
    )

    # 1. Agent WITH credential grant
    authorized_agent = AgentProfile(
        id="authed-agent",
        name="Authed Agent",
        description="Has credentials",
        system_prompt="Helpful agent",
        allowed_tool_names=["dummy_tool"],
        allowed_credentials=["github-pat"],
    )

    call = ToolCall(id="call-1", name="dummy_tool", arguments={})
    res = await registry.execute(call, authorized_agent)
    assert res.success is True
    assert "credentials" in context_seen
    assert context_seen["credentials"]["github-pat"] == "ghp_live_secret_token_abcdef123456"
    assert env_seen["AUTOREIV_CRED_GITHUB_PAT"] == "ghp_live_secret_token_abcdef123456"

    # Verify env is cleaned up after execution
    assert "AUTOREIV_CRED_GITHUB_PAT" not in os.environ

    # 2. Agent WITHOUT credential grant
    context_seen.clear()
    env_seen.clear()

    unauthorized_agent = AgentProfile(
        id="unauthed-agent",
        name="Unauthed Agent",
        description="No credentials",
        system_prompt="Helpful agent",
        allowed_tool_names=["dummy_tool"],
        allowed_credentials=[],
    )

    call2 = ToolCall(id="call-2", name="dummy_tool", arguments={})
    res2 = await registry.execute(call2, unauthorized_agent)
    assert res2.success is True
    assert context_seen.get("credentials", {}) == {}
    assert env_seen.get("AUTOREIV_CRED_GITHUB_PAT") is None
    assert "AUTOREIV_CRED_GITHUB_PAT" not in os.environ


@pytest.mark.asyncio
async def test_agent_kernel_scrubs_secret_from_tool_output(tmp_path):
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    store.initialize_db()

    secret_val = "prod_api_key_secret_xyz999"
    cred = Credential(
        id="cloud-key",
        name="Cloud API Key",
        type="token",
        secret=secret_val,
    )
    store.save_credential(cred)

    registry = ScopedToolRegistry(state_store=store)

    def leaky_tool():
        # Tool accidentally returns secret in output
        return f"Connected with token: {secret_val} successfully!"

    registry.register_tool(
        name="leaky_tool",
        description="A tool that returns secrets",
        parameters={"type": "object", "properties": {}},
        handler=leaky_tool,
    )

    agent = AgentProfile(
        id="worker",
        name="Worker",
        description="Worker",
        system_prompt="Worker",
        allowed_tool_names=["leaky_tool"],
        allowed_credentials=["cloud-key"],
    )

    # Mock gateway
    class DummyGateway:
        pass

    telemetry = TelemetryCollector(store=store)
    kernel = AgentKernel(
        gateway=DummyGateway(),
        tool_registry=registry,
        state_store=store,
        telemetry=telemetry,
    )

    call = ToolCall(id="call-leaky", name="leaky_tool", arguments={})
    tool_res = await kernel.execute_and_scrub_tool(call, agent, session_id="test-session")

    assert tool_res.success is True
    assert secret_val not in str(tool_res.output)
    assert "***MASKED***" in str(tool_res.output)
