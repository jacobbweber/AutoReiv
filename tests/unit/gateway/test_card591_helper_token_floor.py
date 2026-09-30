"""CARD-591: helper calls get 16384 tokens of room (4096 cut nemotron's thinking), never more than a quarter of the window."""

from __future__ import annotations

import pytest

from src.application.kernel.reply_limits import HELPER_MIN_TOKENS
from tests.unit.gateway.test_card586_reply_caps import _gw, _req


def test_helper_floor_is_16384():
    assert HELPER_MIN_TOKENS == 16384


@pytest.mark.asyncio
async def test_helper_floor_respects_a_small_window():
    gw, llm = _gw()
    await gw.complete(_req(max_tokens=250))
    await gw.complete(_req(max_tokens=250, num_ctx=32768))
    await gw.complete(_req(max_tokens=250, num_ctx=2048))
    await gw.complete(_req(max_tokens=9000, num_ctx=16384))
    assert [r.max_tokens for r in llm.requests] == [16384, 8192, 1024, 9000]
