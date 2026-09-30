"""CARD-592: every model-call wait is generous (local models fill the KV cache, think long, queue behind other chats),
the main ones live in Settings > Reply limits (setting > env > default), and short timeouts stay only on probes."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from src.application.kernel import reply_limits
from src.application.kernel.reply_limits import (
    DEFAULT_HELPER_SECONDS,
    DEFAULT_MAX_SECONDS,
    DEFAULT_PHASE_SECONDS,
    DEFAULT_PROVIDER_IDLE_SECONDS,
    helper_call_seconds,
    resolve_all_limits,
    resolve_reply_limits,
    resolve_timeout,
)
from src.application.orchestration import phase_llm_resilience
from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.infrastructure.gateway import timeouts
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

ENV_KEYS = (
    "AUTOREIV_MAX_REPLY_SECONDS",
    "AUTOREIV_MAX_REPLY_TOKENS",
    "AUTOREIV_PROVIDER_IDLE_SECONDS",
    "GATEWAY_DEFAULT_TIMEOUT_SECONDS",
    "STANDING_PHASE_LLM_TIMEOUT_SECONDS",
    "AUTOREIV_HELPER_CALL_SECONDS",
)


@pytest.fixture
def store(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    # phase resolution loads the repo .env; keep the operator's file out of the test
    monkeypatch.setattr(phase_llm_resilience, "load_repo_dotenv", lambda *a, **k: None)
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    yield s
    reply_limits.bind_store(None)
    timeouts.set_provider_idle_resolver(None)


def test_defaults_are_generous(store):
    assert DEFAULT_MAX_SECONDS == 7200
    assert DEFAULT_PROVIDER_IDLE_SECONDS == 1800
    assert DEFAULT_PHASE_SECONDS == 21600
    assert DEFAULT_HELPER_SECONDS == 1800
    assert timeouts.DEFAULT_PROVIDER_READ_TIMEOUT == 1800.0
    assert phase_llm_resilience.STANDING_PHASE_LLM_TIMEOUT_SECONDS == 21600.0
    assert resolve_all_limits(store) == {
        "max_tokens": 32768,
        "max_seconds": 7200,
        "provider_idle_seconds": 1800,
        "phase_seconds": 21600,
        "helper_seconds": 1800,
    }


def test_setting_beats_env_beats_default(store, monkeypatch):
    monkeypatch.setenv("AUTOREIV_HELPER_CALL_SECONDS", "90")
    assert resolve_timeout("helper_seconds", store) == 90
    store.set_setting("reply_limits", {"helper_seconds": 45, "max_seconds": 9000})
    assert resolve_timeout("helper_seconds", store) == 45
    assert resolve_reply_limits(store)[1] == 9000
    reply_limits.bind_store(store)
    assert helper_call_seconds() == 45.0


def test_phase_timeout_follows_the_setting_then_env(store, monkeypatch):
    reply_limits.bind_store(store)
    assert phase_llm_resilience.resolve_standing_phase_llm_timeout() == 21600.0
    monkeypatch.setenv("STANDING_PHASE_LLM_TIMEOUT_SECONDS", "1800")
    assert phase_llm_resilience.resolve_standing_phase_llm_timeout() == 1800.0
    store.set_setting("reply_limits", {"phase_seconds": 36000})
    assert phase_llm_resilience.resolve_standing_phase_llm_timeout() == 36000.0


def test_provider_silence_follows_the_saved_setting_per_request(store, monkeypatch):
    monkeypatch.setenv("GATEWAY_DEFAULT_TIMEOUT_SECONDS", "180")  # legacy env still read
    adapter = OpenAIProviderAdapter(base_url="http://spark:8099/v1", provider_id="vllm")
    assert adapter.timeout == 180.0
    timeouts.set_provider_idle_resolver(lambda: reply_limits.saved_timeout("provider_idle_seconds", store))
    assert adapter.timeout == 180.0  # nothing saved yet
    store.set_setting("reply_limits", {"provider_idle_seconds": 3600})
    assert adapter.timeout == 3600.0  # no restart, same adapter
    assert OpenAIProviderAdapter(timeout=5.0).timeout == 5.0  # an explicit value still wins


@pytest.mark.asyncio
async def test_model_calls_send_the_generous_timeout_and_probes_stay_short(store):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen[request.url.path] = request.extensions.get("timeout")
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={
            "id": "x", "model": "m", "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                                                  "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    timeouts.set_provider_idle_resolver(lambda: 2400.0)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://spark:8099/v1")
    adapter = OpenAIProviderAdapter(base_url="http://spark:8099/v1", client=client, provider_id="vllm")
    req = CompletionRequest(model="vllm/m", messages=[ChatMessage(role=Role.USER, content="hi")])
    await adapter.complete(req)
    sent = seen["/v1/chat/completions"]
    assert sent["read"] == 2400.0 and sent["connect"] == 60.0 and sent["write"] == 600.0 and sent["pool"] == 600.0
    await adapter.list_models()
    assert seen["/v1/models"]["read"] == timeouts.PROBE_TIMEOUT == 15.0


@pytest.mark.asyncio
async def test_ollama_stream_sends_the_generous_timeout(store):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, content=b'{"message":{"role":"assistant","content":"ok"},"done":true}\n')

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://nimo:11434")
    adapter = OllamaProviderAdapter(base_url="http://nimo:11434", client=client)
    req = CompletionRequest(model="ollama/qwen", messages=[ChatMessage(role=Role.USER, content="hi")], stream=True)
    async for _ in adapter.stream(req):
        pass
    assert seen["timeout"]["read"] == 1800.0


def test_reply_limits_api_has_the_new_fields(store):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.web.routers.settings import router

    app = FastAPI()
    app.include_router(router)
    app.state.store = store
    client = TestClient(app)
    got = client.get("/api/settings/reply-limits").json()
    assert (got["max_seconds"], got["provider_idle_seconds"], got["phase_seconds"], got["helper_seconds"]) == (
        7200, 1800, 21600, 1800)
    got = client.put("/api/settings/reply-limits", json={"provider_idle_seconds": 3600, "phase_seconds": 43200}).json()
    assert (got["provider_idle_seconds"], got["phase_seconds"], got["max_seconds"]) == (3600, 43200, 7200)
    got = client.put("/api/settings/reply-limits", json={"provider_idle_seconds": 0}).json()
    assert got["provider_idle_seconds"] == 1800
    assert client.put("/api/settings/reply-limits", json={"helper_seconds": -1}).status_code == 400


@pytest.mark.asyncio
async def test_chat_stream_sends_keepalive_comments_while_idle():
    from src.web.routers.chat import SSE_KEEPALIVE, sse_with_keepalive

    queue: asyncio.Queue = asyncio.Queue()

    async def later():
        await asyncio.sleep(0.12)
        await queue.put("data: {}\n\n")
        await queue.put(None)

    task = asyncio.create_task(later())
    items = [item async for item in sse_with_keepalive(queue, interval=0.03)]
    await task
    assert items[-1] == "data: {}\n\n"
    assert items.count(SSE_KEEPALIVE) >= 2
    assert SSE_KEEPALIVE.startswith(":")  # an SSE comment: parsers skip it


def test_job_budgets_are_very_large():
    from src.domain.orchestration.models import Job

    job = Job(id="j", goal="g", session_id="s", agent_id="a")
    assert job.budget_max_phases == 256 and job.budget_max_handoffs == 64


def test_tool_defaults_are_long_but_discovery_stays_short():
    from src.application.skills.sandbox_tools import SandboxExecutionTools
    from src.infrastructure.mcp.client_adapter import DISCOVERY_TIMEOUT_SECONDS, MCPClientAdapter

    assert SandboxExecutionTools().default_timeout_seconds == 600.0
    mcp = MCPClientAdapter(server_name="x", command=["x"])
    assert mcp.timeout_seconds == 600.0
    assert mcp._discovery_timeout() == DISCOVERY_TIMEOUT_SECONDS == 30.0
