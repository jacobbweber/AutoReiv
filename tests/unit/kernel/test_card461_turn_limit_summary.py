"""CARD-461: at the turn limit the reply is a short no-tools summary + footer, never "Execution terminated"."""

from __future__ import annotations

import pathlib
from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.kernel.turn_limit import turn_limit_fallback, turn_limit_footer
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.domain.orchestration.models import ReactState

SUMMARY = "Read README. AGENTS and CHANGELOG are left."


class StepLLM(LLMProviderPort):
    """Every tool-enabled step asks for a new file (no loop); the no-tools call gives `final`."""

    provider_id = "mock"

    def __init__(self, final=SUMMARY, final_tool=False, boom=False):
        self.final, self.final_tool, self.boom = final, final_tool, boom
        self.requests: List[CompletionRequest] = []

    def _step(self, request):
        n = len(self.requests)
        return ToolCall(id=f"c{n}", name="read_file_x", arguments={"name": f"f{n}.md"})

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if request.tools:
            msg = ChatMessage(role=Role.ASSISTANT, content="", tool_calls=[self._step(request)])
            return CompletionResponse(model=request.model, message=msg, finish_reason="tool_calls")
        if self.boom:
            raise RuntimeError("provider down")
        calls = [ToolCall(id="x", name="read_file_x", arguments={"name": "z"})] if self.final_tool else None
        msg = ChatMessage(role=Role.ASSISTANT, content=self.final, tool_calls=calls)
        return CompletionResponse(model=request.model, message=msg, finish_reason="stop")

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        yield StreamChunk(tool_calls=[self._step(request)], is_finished=True, finish_reason="tool_calls")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


def _kernel(llm):
    from src.infrastructure.memory.sqlite_store import SQLiteStateStore

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    ran = []

    def read_file_x(name):
        ran.append(name)
        return {"name": name, "text": f"contents of {name}"}

    reg = ScopedToolRegistry()
    reg.register_tool(name="read_file_x", description="read", handler=read_file_x,
                      parameters={"type": "object", "properties": {"name": {"type": "string"}}})
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    flushed = []
    kernel._ace_flush_failed_turn = lambda **kw: flushed.append(kw)
    agent = AgentProfile(id="developer", name="D", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:read_file_x"], max_turns=2)
    return kernel, store, agent, ran, flushed


@pytest.mark.asyncio
async def test_sync_limit_ends_with_summary_and_footer():
    llm = StepLLM()
    kernel, store, agent, ran, flushed = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    msg = await kernel.run_turn(agent=agent, session_id=session.id, user_content="read three files")
    assert len(llm.requests) == 3 and not llm.requests[-1].tools
    assert msg.content == f"{SUMMARY}\n\n{turn_limit_footer(2)}"
    assert kernel.react_state == ReactState.FAILED
    assert flushed[-1]["failed"] is True and flushed[-1]["error_message"] == "turn_limit"
    assert store.get_messages(session.id)[-1].content == msg.content


@pytest.mark.asyncio
async def test_stream_limit_streams_summary_then_turn_end():
    llm = StepLLM()
    kernel, store, agent, ran, flushed = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="read")]
    expected = f"{SUMMARY}\n\n{turn_limit_footer(2)}"
    assert events[-1].event_type == KernelEventType.TURN_END and events[-1].content == expected
    assert any(e.event_type == KernelEventType.TOKEN and e.content == expected for e in events)
    assert not llm.requests[-1].tools
    assert store.get_messages(session.id)[-1].content == expected
    assert kernel.react_state == ReactState.FAILED


@pytest.mark.asyncio
@pytest.mark.parametrize("kw", [{"boom": True}, {"final": ""}, {"final": "", "final_tool": True}])
async def test_failed_or_empty_final_call_uses_fallback_and_runs_no_tool(kw):
    llm = StepLLM(**kw)
    kernel, store, agent, ran, flushed = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    msg = await kernel.run_turn(agent=agent, session_id=session.id, user_content="read")
    assert msg.content == turn_limit_fallback(2)
    assert len(ran) == 2  # only the two budgeted steps ran a tool


@pytest.mark.asyncio
async def test_keep_going_sees_the_stopped_reply_tool_results():
    llm = StepLLM()
    kernel, store, agent, ran, flushed = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    await kernel.run_turn(agent=agent, session_id=session.id, user_content="read")
    before = len(llm.requests)
    await kernel.run_turn(agent=agent, session_id=session.id, user_content="keep going")
    first_new = llm.requests[before]
    tool_texts = [m.content for m in first_new.messages if m.role == Role.TOOL]
    assert any("contents of" in (t or "") for t in tool_texts)
    assert first_new.tools  # fresh budget: the next reply can call tools again


def test_old_terminator_is_gone_from_src():
    root = pathlib.Path(__file__).resolve().parents[3] / "src"
    hits = [p for p in root.rglob("*.py") if "Max turn budget of" in p.read_text(encoding="utf-8", errors="ignore")]
    assert hits == []
