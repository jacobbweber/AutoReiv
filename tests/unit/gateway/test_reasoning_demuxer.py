"""
Unit tests for Reasoning Tag Demuxer [REQ-GW-006].
"""

import pytest

from src.application.gateway.demuxer import ReasoningDemuxer
from src.domain.gateway.models import StreamChunk


async def async_generator_from_chunks(chunks):
    for c in chunks:
        yield c


@pytest.mark.asyncio
async def test_demuxer_passthrough_plain_text():
    raw_chunks = [
        StreamChunk(content="Hello "),
        StreamChunk(content="world!"),
        StreamChunk(is_finished=True, finish_reason="stop"),
    ]
    demuxer = ReasoningDemuxer()
    results = []
    async for item in demuxer.demux_stream(async_generator_from_chunks(raw_chunks)):
        results.append(item)

    assert len(results) == 3
    assert results[0].content == "Hello "
    assert results[0].reasoning_content == ""
    assert results[1].content == "world!"
    assert results[1].reasoning_content == ""
    assert results[2].is_finished is True


@pytest.mark.asyncio
async def test_demuxer_single_chunk_think_block():
    raw_chunks = [
        StreamChunk(content="<think>Analyzing request</think>The final answer is 42."),
        StreamChunk(is_finished=True),
    ]
    demuxer = ReasoningDemuxer()
    results = []
    async for item in demuxer.demux_stream(async_generator_from_chunks(raw_chunks)):
        results.append(item)

    combined_reasoning = "".join(r.reasoning_content for r in results)
    combined_content = "".join(r.content for r in results)

    assert combined_reasoning == "Analyzing request"
    assert combined_content == "The final answer is 42."


@pytest.mark.asyncio
async def test_demuxer_split_chunks_inside_and_outside():
    raw_chunks = [
        StreamChunk(content="<think>"),
        StreamChunk(content="Step 1: calculate. "),
        StreamChunk(content="Step 2: verify."),
        StreamChunk(content="</think>"),
        StreamChunk(content="Answer is ready."),
        StreamChunk(is_finished=True),
    ]
    demuxer = ReasoningDemuxer()
    results = []
    async for item in demuxer.demux_stream(async_generator_from_chunks(raw_chunks)):
        results.append(item)

    combined_reasoning = "".join(r.reasoning_content for r in results)
    combined_content = "".join(r.content for r in results)

    assert combined_reasoning == "Step 1: calculate. Step 2: verify."
    assert combined_content == "Answer is ready."


@pytest.mark.asyncio
async def test_demuxer_partial_tag_across_chunks():
    raw_chunks = [
        StreamChunk(content="<thi"),
        StreamChunk(content="nk>Deep thinking"),
        StreamChunk(content="</thi"),
        StreamChunk(content="nk>Result text"),
    ]
    demuxer = ReasoningDemuxer()
    results = []
    async for item in demuxer.demux_stream(async_generator_from_chunks(raw_chunks)):
        results.append(item)

    combined_reasoning = "".join(r.reasoning_content for r in results)
    combined_content = "".join(r.content for r in results)

    assert combined_reasoning == "Deep thinking"
    assert combined_content == "Result text"
