"""CARD-585: generation slot pools per provider endpoint plus a background pool; the reply time limit starts at the
model's first token (default 1200 s); a stopped reply closes the provider stream (so the server stops generating)."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.generation_semaphore import GenerationPools, provider_pool_key
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk
from src.domain.kernel.models import AgentProfile, AgentTone, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class _Provider(LLMProviderPort):
    def __init__(self, provider_id: str, base_url: str, script=None, hold: asyncio.Event | None = None):
        self.provider_id = provider_id
        self.base_url = base_url
        self.script = script
        self.hold = hold
        self.in_flight = 0
        self.closed = 0
        self.started = asyncio.Event()

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.in_flight += 1
        self.started.set()
        try:
            if self.hold is not None:
                await self.hold.wait()
            return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content="ok"))
        finally:
            self.in_flight -= 1

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.in_flight += 1
        self.started.set()
        try:
            if self.hold is not None:
                await self.hold.wait()
            if self.script is None:
                yield StreamChunk(content="ok", is_finished=True, finish_reason="stop")
            else:
                async for c in self.script():
                    yield c
        finally:
            self.in_flight -= 1
            self.closed += 1


def _req(model: str, background: bool = False) -> CompletionRequest:
    return CompletionRequest(model=model, messages=[ChatMessage(role=Role.USER, content="hi")], background=background)


def test_pool_key_is_the_endpoint():
    class P:
        def __init__(self, pid, url):
            self.provider_id, self.base_url = pid, url

    spark = provider_pool_key(P("vllm", "http://192.168.1.218:8099/v1"))
    assert spark == "192.168.1.218:8099"
    assert provider_pool_key(P("architect-override", "http://192.168.1.218:8099/v1/")) == spark
    assert provider_pool_key(P("ollama", "http://192.168.1.29:11434")) == "192.168.1.29:11434"
    assert provider_pool_key(P("ollama", "http://localhost:11434")) == "127.0.0.1:11434"
    assert provider_pool_key(P("openai", "https://api.openai.com/v1")) == "api.openai.com:443"
    assert provider_pool_key(P("mock", "")) == "provider:mock"


def test_cap_change_resizes_every_provider_pool_not_background():
    pools = GenerationPools(1)
    a, b = pools.pool("a:1"), pools.pool("b:2")
    pools.set_max_concurrent(3)
    assert (a.max_concurrent, b.max_concurrent, pools.pool("c:3").max_concurrent) == (3, 3, 3)
    assert pools.background.max_concurrent == 1
    assert set(pools.snapshot()) == {"a:1", "b:2", "c:3", "background"}


@pytest.mark.asyncio
async def test_a_busy_spark_slot_does_not_block_nimo():
    hold = asyncio.Event()
    spark = _Provider("vllm", "http://192.168.1.218:8099/v1", hold=hold)
    nimo = _Provider("ollama", "http://192.168.1.29:11434")
    gw = MultiProviderGateway(max_concurrent_generations=1)
    gw.register_provider(spark)
    gw.register_provider(nimo)
    spark_task = asyncio.create_task(gw.complete(_req("vllm/qwen")))
    await asyncio.wait_for(spark.started.wait(), 2)
    resp = await asyncio.wait_for(gw.complete(_req("ollama/qwen3.8:latest")), 2)  # would hang on one shared pool
    assert resp.message.content == "ok" and spark.in_flight == 1
    hold.set()
    await spark_task


@pytest.mark.asyncio
async def test_same_provider_still_queues_at_the_cap():
    hold = asyncio.Event()
    spark = _Provider("vllm", "http://192.168.1.218:8099/v1", hold=hold)
    gw = MultiProviderGateway(max_concurrent_generations=1)
    gw.register_provider(spark)
    first = asyncio.create_task(gw.complete(_req("vllm/a")))
    await asyncio.wait_for(spark.started.wait(), 2)
    second = asyncio.create_task(gw.complete(_req("vllm/b")))
    await asyncio.sleep(0.05)
    assert spark.in_flight == 1 and not second.done()
    hold.set()
    await asyncio.gather(first, second)


@pytest.mark.asyncio
async def test_background_calls_use_their_own_pool():
    hold = asyncio.Event()
    spark = _Provider("vllm", "http://192.168.1.218:8099/v1", hold=hold)
    gw = MultiProviderGateway(max_concurrent_generations=1)
    gw.register_provider(spark)
    fg = asyncio.create_task(gw.complete(_req("vllm/a")))
    await asyncio.wait_for(spark.started.wait(), 2)
    assert gw.generation_slot_for(_req("vllm/a", background=True)) is gw.generation_pools.background
    bg = asyncio.create_task(gw.complete(_req("vllm/a", background=True)))
    await asyncio.sleep(0.05)
    assert spark.in_flight == 2  # the background call reached the provider while the chat reply held its slot
    hold.set()
    await asyncio.gather(fg, bg)


# ---- kernel: time limit from the first token -------------------------------------------------------------------------


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


PROFILE = AgentProfile(id="architect", name="Architect", description="d", system_prompt="s", tone=AgentTone.TECHNICAL)


def _kernel(store, provider, cap=1):
    gw = MultiProviderGateway(max_concurrent_generations=cap)
    gw.register_provider(provider)
    k = AgentKernel(gateway=gw, tool_registry=ScopedToolRegistry(), state_store=store, telemetry=TelemetryCollector(store=store))
    k._resolve_context_limit = lambda *a, **kw: 65536
    return k, gw


async def _run(kernel, store, text="hi"):
    session = store.create_session(agent_id=PROFILE.id, title="t")
    events = [ev async for ev in kernel.stream_turn(agent=PROFILE, session_id=session.id, user_content=text)]
    saved = [m.content for m in store.get_messages(session.id) if m.role == Role.ASSISTANT]
    return events, saved


def test_default_reply_seconds_is_7200():
    from src.application.kernel.reply_limits import DEFAULT_MAX_SECONDS

    assert DEFAULT_MAX_SECONDS == 7200  # CARD-592 (CARD-585 had 1200)


@pytest.mark.asyncio
async def test_slow_start_does_not_count_toward_the_time_limit(store):
    async def slow_start():
        await asyncio.sleep(1.5)  # queue / prefill / model load before the first token
        yield StreamChunk(content="pong", is_finished=True, finish_reason="stop")

    store.set_setting("reply_limits", {"max_seconds": 1})
    kernel, _ = _kernel(store, _Provider("mock", "", script=slow_start))
    events, saved = await asyncio.wait_for(_run(kernel, store), 20)
    assert saved[-1] == "pong"
    assert not [e for e in events if e.event_type == KernelEventType.ERROR]


@pytest.mark.asyncio
async def test_waiting_for_a_slot_does_not_count_toward_the_time_limit(store):
    hold = asyncio.Event()
    busy = _Provider("mock", "", hold=hold)
    store.set_setting("reply_limits", {"max_seconds": 1})
    kernel, gw = _kernel(store, busy)
    blocker = asyncio.create_task(gw.complete(_req("mock/x")))  # holds the only slot
    await asyncio.wait_for(busy.started.wait(), 2)
    turn = asyncio.create_task(_run(kernel, store))
    await asyncio.sleep(1.5)
    hold.set()
    events, saved = await asyncio.wait_for(turn, 20)
    await blocker
    assert saved[-1] == "ok"
    assert not [e for e in events if e.event_type == KernelEventType.ERROR]


@pytest.mark.asyncio
async def test_time_limit_still_stops_after_the_first_token_and_closes_the_stream(store):
    async def endless():
        while True:
            yield StreamChunk(reasoning_content="hmm ")
            await asyncio.sleep(0.01)

    store.set_setting("reply_limits", {"max_seconds": 1})
    provider = _Provider("mock", "", script=endless)
    kernel, _ = _kernel(store, provider)
    events, saved = await asyncio.wait_for(_run(kernel, store), 20)
    errors = [e.content for e in events if e.event_type == KernelEventType.ERROR]
    assert errors and "time limit of 1 s" in errors[-1] and "first token" in errors[-1]
    assert provider.closed == 1 and provider.in_flight == 0  # the HTTP stream was closed, so the server stops


@pytest.mark.asyncio
async def test_stop_cancels_the_turn_and_closes_the_provider_stream(store):
    started = asyncio.Event()

    async def endless():
        started.set()
        while True:
            yield StreamChunk(content="x")
            await asyncio.sleep(0.01)

    provider = _Provider("mock", "", script=endless)
    kernel, _ = _kernel(store, provider)
    turn = asyncio.create_task(_run(kernel, store))
    await asyncio.wait_for(started.wait(), 5)
    turn.cancel()  # what Stop (abort) does to the worker task
    with pytest.raises(asyncio.CancelledError):
        await turn
    await asyncio.sleep(0.05)
    assert provider.closed == 1 and provider.in_flight == 0
