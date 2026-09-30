"""CARD-551 + CARD-460: an identical tool call right after itself is not run again (the earlier result comes back);
when the loop continues, one last no-tools call answers from the tool results instead of "Execution terminated"."""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.repeat_guard import LOOP_FALLBACK_MESSAGE, REPEAT_SAFE_TOOLS, RepeatGuard
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType, ToolResult
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class LoopingLLM(LLMProviderPort):
    """Streams the same tool call every step; complete() is the final no-tools answer."""

    provider_id = "mock"

    def __init__(self, final_text: str = "High tide is at 14:05."):
        self.final_text = final_text
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content=self.final_text),
                                  finish_reason="stop")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        tc = ToolCall(id=f"c{len(self.requests)}", name="harbor_tide", arguments={"harbor": "north"})
        yield StreamChunk(tool_calls=[tc], is_finished=True, finish_reason="tool_calls")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


def _kernel(llm):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    calls = []

    def harbor_tide(harbor):
        calls.append(harbor)
        return {"harbor": harbor, "high_tide": "14:05"}

    reg = ScopedToolRegistry()
    reg.register_tool(name="harbor_tide", description="tide", handler=harbor_tide,
                      parameters={"type": "object", "properties": {"harbor": {"type": "string"}}})
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:harbor_tide"], max_turns=10)
    return kernel, store, agent, calls


async def _run(kernel, store, agent):
    session = store.create_session(agent_id=agent.id, title="t")
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="When is high tide?")]
    return events, store.get_messages(session.id)


@pytest.mark.asyncio
async def test_loop_ends_with_an_answer_from_the_tool_result():
    llm = LoopingLLM()
    kernel, store, agent, calls = _kernel(llm)
    events, saved = await _run(kernel, store, agent)
    end = [e for e in events if e.event_type == KernelEventType.TURN_END][-1]
    assert end.content == "High tide is at 14:05."
    assert "Execution terminated" not in end.content
    assert calls == ["north"]  # the identical second call was not run again
    reused = [m for m in saved if m.role == Role.TOOL and "already_done" in (m.content or "")]
    assert reused, "the second identical call gets the earlier result back"
    final_req = llm.requests[-1]
    assert final_req.tools is None and "Do not call any tools" in final_req.messages[-1].content
    assert saved[-1].content == "High tide is at 14:05."


@pytest.mark.asyncio
async def test_empty_final_answer_falls_back_to_a_plain_message():
    llm = LoopingLLM(final_text="")
    kernel, store, agent, _ = _kernel(llm)
    events, saved = await _run(kernel, store, agent)
    assert saved[-1].content == LOOP_FALLBACK_MESSAGE


def test_repeat_guard_reuses_only_the_previous_step_and_skips_poll_tools():
    g = RepeatGuard()
    tc = ToolCall(id="1", name="read_project_file", arguments={"path": "a.py"})
    assert g.reuse(tc) is None
    g.record(tc, ToolResult(call_id="1", tool_name=tc.name, output="A"))
    g.next_step()
    again = g.reuse(ToolCall(id="2", name="read_project_file", arguments={"path": "a.py"}))
    assert again is not None and again.output["result"] == "A" and again.output["already_done"]
    assert g.reuse(ToolCall(id="3", name="read_project_file", arguments={"path": "b.py"})) is None
    g.next_step()
    g.next_step()
    assert g.reuse(tc) is None  # only the immediately previous step counts
    poll = ToolCall(id="4", name=sorted(REPEAT_SAFE_TOOLS)[0], arguments={})
    g.record(poll, ToolResult(call_id="4", tool_name=poll.name, output="x"))
    g.next_step()
    assert g.reuse(poll) is None
    parked = ToolCall(id="5", name="write_card", arguments={"x": 1})
    g.record(parked, ToolResult(call_id="5", tool_name="write_card", output={"status": "approval_required"}))
    g.next_step()
    assert g.reuse(parked) is None
