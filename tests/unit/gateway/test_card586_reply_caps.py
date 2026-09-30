"""CARD-586: every model call carries a max-token limit (default 32768, Settings > Reply limits); helper calls get room
to think; a user-set limit on chat replies is kept."""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.reply_limits import DEFAULT_MAX_TOKENS, HELPER_MIN_TOKENS
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk


class _LLM(LLMProviderPort):
    provider_id = "mock"

    def __init__(self):
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content="ok"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        yield StreamChunk(content="ok", is_finished=True, finish_reason="stop")


def _gw(resolver=None):
    llm = _LLM()
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    if resolver is not None:
        gw.set_reply_cap_resolver(resolver)
    return gw, llm


def _req(**kw) -> CompletionRequest:
    return CompletionRequest(model="mock/x", messages=[ChatMessage(role=Role.USER, content="hi")], **kw)


async def _drain(gw, req):
    return [c async for c in gw.stream(req, demux_reasoning=False)]


def test_default_is_32768():
    assert DEFAULT_MAX_TOKENS == 32768


@pytest.mark.asyncio
async def test_a_call_without_max_tokens_gets_the_default():
    gw, llm = _gw()
    await gw.complete(_req())  # plan / reflexion calls used to send no limit at all
    await _drain(gw, _req())
    assert [r.max_tokens for r in llm.requests] == [32768, 32768]


@pytest.mark.asyncio
async def test_the_settings_value_is_used_and_capped_at_a_quarter_of_the_window():
    gw, llm = _gw(lambda: 50000)
    await _drain(gw, _req())
    await _drain(gw, _req(num_ctx=65536))
    assert [r.max_tokens for r in llm.requests] == [50000, 16384]


@pytest.mark.asyncio
async def test_a_broken_resolver_falls_back_to_the_default():
    def boom():
        raise RuntimeError("store gone")

    gw, llm = _gw(boom)
    await gw.complete(_req())
    assert llm.requests[0].max_tokens == 32768


@pytest.mark.asyncio
async def test_small_helper_caps_get_room_to_think_but_chat_limits_are_kept():
    gw, llm = _gw()
    await gw.complete(_req(max_tokens=250))  # capability detector
    await gw.complete(_req(max_tokens=8000))
    await _drain(gw, _req(max_tokens=200))  # a chat reply with the user's own Settings limit
    assert [r.max_tokens for r in llm.requests] == [HELPER_MIN_TOKENS, 8000, 200]
