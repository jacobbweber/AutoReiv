"""CARD-567: a runaway model reply stops at a reply limit (tokens or seconds) with a clear message instead of hanging."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class _LLM(LLMProviderPort):
    provider_id: str = "mock"

    def __init__(self, script):
        self.script = script
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content="x"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        async for c in self.script():
            yield c


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def _kernel(store, script, ctx=65536):
    llm = _LLM(script)
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    k = AgentKernel(gateway=gw, tool_registry=ScopedToolRegistry(), state_store=store, telemetry=TelemetryCollector(store=store))
    k._resolve_context_limit = lambda *a, **kw: ctx
    return k, llm


PROFILE = AgentProfile(id="architect", name="Architect", description="d", system_prompt="s", tone=AgentTone.TECHNICAL)


async def _run(kernel, store, text="Think it through"):
    session = store.create_session(agent_id=PROFILE.id, title="t")
    events = [ev async for ev in kernel.stream_turn(agent=PROFILE, session_id=session.id, user_content=text)]
    saved = [m.content for m in store.get_messages(session.id) if m.role == Role.ASSISTANT]
    return events, saved


async def _normal():
    yield StreamChunk(content="pong", is_finished=True, finish_reason="stop")


async def _endless():
    while True:
        yield StreamChunk(reasoning_content="hmm ")
        await asyncio.sleep(0.01)


async def _length_while_thinking():
    yield StreamChunk(reasoning_content="step 1, step 2, step 3 ")
    yield StreamChunk(is_finished=True, finish_reason="length")


async def _length_mid_answer():
    yield StreamChunk(content="Part one of the answer")
    yield StreamChunk(is_finished=True, finish_reason="length")


def test_limits_resolve_setting_then_env_then_default(store, monkeypatch):
    from src.application.kernel.reply_limits import DEFAULT_MAX_SECONDS, DEFAULT_MAX_TOKENS, resolve_reply_limits

    monkeypatch.delenv("AUTOREIV_MAX_REPLY_TOKENS", raising=False)
    monkeypatch.delenv("AUTOREIV_MAX_REPLY_SECONDS", raising=False)
    assert resolve_reply_limits(store) == (DEFAULT_MAX_TOKENS, DEFAULT_MAX_SECONDS)
    monkeypatch.setenv("AUTOREIV_MAX_REPLY_TOKENS", "5000")
    assert resolve_reply_limits(store)[0] == 5000
    store.set_setting("reply_limits", {"max_tokens": 300, "max_seconds": 7})
    assert resolve_reply_limits(store) == (300, 7)


@pytest.mark.asyncio
async def test_streaming_request_carries_the_reply_token_limit(store):
    kernel, llm = _kernel(store, _normal)
    events, saved = await _run(kernel, store, "pong")
    req = llm.requests[0]
    assert req.max_tokens == 16384  # default, under a quarter of the 64k window
    assert saved[-1] == "pong" and not [e for e in events if e.event_type == KernelEventType.ERROR]  # normal reply unchanged


@pytest.mark.asyncio
async def test_token_limit_is_capped_by_the_context_window(store):
    kernel, llm = _kernel(store, _normal, ctx=16384)
    await _run(kernel, store, "pong")
    assert llm.requests[0].max_tokens == 4096


@pytest.mark.asyncio
async def test_a_reply_that_never_ends_stops_at_max_seconds_with_a_message(store):
    store.set_setting("reply_limits", {"max_seconds": 1})
    kernel, _ = _kernel(store, _endless)
    events, saved = await asyncio.wait_for(_run(kernel, store), timeout=20)
    errors = [e.content for e in events if e.event_type == KernelEventType.ERROR]
    assert errors and "time limit" in errors[-1] and "1 s" in errors[-1]
    assert saved and "time limit" in saved[-1]


@pytest.mark.asyncio
async def test_token_limit_while_still_thinking_gives_the_message(store):
    store.set_setting("reply_limits", {"max_tokens": 200})
    kernel, llm = _kernel(store, _length_while_thinking)
    events, saved = await _run(kernel, store)
    assert llm.requests[0].max_tokens == 200
    errors = [e.content for e in events if e.event_type == KernelEventType.ERROR]
    assert errors and "reply limit" in errors[-1] and "200 tokens" in errors[-1]
    assert saved and "reply limit" in saved[-1]


@pytest.mark.asyncio
async def test_a_cut_answer_keeps_its_text_and_says_it_was_cut(store):
    store.set_setting("reply_limits", {"max_tokens": 200})
    kernel, _ = _kernel(store, _length_mid_answer)
    events, saved = await _run(kernel, store)
    assert saved[-1].startswith("Part one of the answer") and "reply limit" in saved[-1]
    assert not [e for e in events if e.event_type == KernelEventType.ERROR]


def test_reply_limits_api_reads_saves_and_clears(store, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.web.routers.settings import router

    monkeypatch.delenv("AUTOREIV_MAX_REPLY_TOKENS", raising=False)
    monkeypatch.delenv("AUTOREIV_MAX_REPLY_SECONDS", raising=False)
    app = FastAPI()
    app.include_router(router)
    app.state.store = store
    client = TestClient(app)
    assert client.get("/api/settings/reply-limits").json()["max_tokens"] == 16384
    got = client.put("/api/settings/reply-limits", json={"max_tokens": 200, "max_seconds": 5}).json()
    assert (got["max_tokens"], got["max_seconds"]) == (200, 5)
    got = client.put("/api/settings/reply-limits", json={"max_tokens": None}).json()
    assert (got["max_tokens"], got["max_seconds"]) == (16384, 5)
    assert client.put("/api/settings/reply-limits", json={"max_seconds": "abc"}).status_code == 400
