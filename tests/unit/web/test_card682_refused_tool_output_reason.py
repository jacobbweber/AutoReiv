"""CARD-682: the chat stream's tool_output event for a refused or failed call carries the reason."""

import asyncio
import json

import pytest

from src.domain.kernel.models import KernelEvent, KernelEventType, ToolResult
from src.web.routers.chat import _forward_kernel_event

REASON = (
    "tool_not_offered:Tool 'wiki_template_search' was not in the tools sent on this call, so it is not "
    "authorized here. Did you mean wiki_template_list?"
)


async def _emit(result: ToolResult, name: str) -> dict:
    queue: asyncio.Queue = asyncio.Queue()
    event = KernelEvent(
        event_type=KernelEventType.TOOL_END,
        tool_call={"id": "c1", "name": name, "arguments": {}},
        tool_result=result,
    )
    await _forward_kernel_event(queue, event, None)
    frame = await queue.get()
    head, data = frame.strip().split("\n", 1)
    assert head == "event: tool_output"
    return json.loads(data[len("data: ") :])


@pytest.mark.asyncio
async def test_refused_call_carries_success_false_and_the_reason():
    ev = await _emit(
        ToolResult(call_id="c1", tool_name="wiki_template_search", output=None, success=False, error=REASON),
        "wiki_template_search",
    )
    assert ev["type"] == "tool_output"
    assert ev["tool_name"] == "wiki_template_search"
    assert ev["success"] is False
    assert ev["error"] == REASON
    assert ev["result"] == f"Tool Error: {REASON}"  # same text the model saw, never null


@pytest.mark.asyncio
async def test_successful_call_is_unchanged_and_says_success():
    ev = await _emit(
        ToolResult(call_id="c1", tool_name="wiki_template_list", output=[{"slug": "a"}], success=True),
        "wiki_template_list",
    )
    assert ev["success"] is True
    assert ev["result"] == [{"slug": "a"}]
    assert ev["tool_name"] == "wiki_template_list"
    assert ev.get("error") is None


@pytest.mark.asyncio
async def test_failure_without_error_text_still_says_why():
    ev = await _emit(ToolResult(call_id="c1", tool_name="x", output=None, success=False, error=None), "x")
    assert ev["success"] is False
    assert ev["result"] == "Tool Error: Tool execution error"
