"""CARD-605: at most 4 wiki look-ups (wiki_note_search / wiki_note_list) per reply.

Past the budget, a look-up is not run; the model gets "Not run: ..." and is told to answer with what it has.
"""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.kernel.wiki_budget import WIKI_LOOKUP_BUDGET, WIKI_LOOKUP_HINT, WikiLookupBudget
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

REPLY = "No notes about weekly planning were found."


class ScriptLLM(LLMProviderPort):
    """stream(): scripted steps (a list of ToolCalls or a reply text). complete(): the checker's answer."""

    provider_id = "mock"

    def __init__(self, steps, check_answer: str = "ALL DONE"):
        self.steps = list(steps)
        self.check_answer = check_answer
        self.streams: List[CompletionRequest] = []
        self.completes: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.completes.append(request)
        if request.tools is None and "check whether an assistant's reply" in (request.messages[-1].content or ""):
            return CompletionResponse(model=request.model, finish_reason="stop",
                                      message=ChatMessage(role=Role.ASSISTANT, content=self.check_answer))
        step = self.steps.pop(0)
        if isinstance(step, str):
            return CompletionResponse(model=request.model, finish_reason="stop",
                                      message=ChatMessage(role=Role.ASSISTANT, content=step))
        return CompletionResponse(model=request.model, finish_reason="tool_calls",
                                  message=ChatMessage(role=Role.ASSISTANT, content="", tool_calls=step))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.streams.append(request)
        assert self.steps, "the kernel made a model call the script did not expect"
        step = self.steps.pop(0)
        if isinstance(step, str):
            yield StreamChunk(content=step)
            yield StreamChunk(is_finished=True, finish_reason="stop")
        else:
            yield StreamChunk(tool_calls=step, is_finished=True, finish_reason="tool_calls")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


def _kernel(llm):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    ran = []
    reg = ScopedToolRegistry()
    reg.register_tool(name="wiki_note_search", description="s",
                      handler=lambda query: ran.append(("search", query)) or {"results": []},
                      parameters={"type": "object", "properties": {"query": {"type": "string"}}})
    reg.register_tool(name="wiki_note_list", description="l",
                      handler=lambda folder: ran.append(("list", folder)) or {"notes": []},
                      parameters={"type": "object", "properties": {"folder": {"type": "string"}}})
    reg.register_tool(name="wiki_note_read", description="r",
                      handler=lambda path: ran.append(("read", path)) or {"text": "x"},
                      parameters={"type": "object", "properties": {"path": {"type": "string"}}})
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:wiki_note_search", "tool:wiki_note_list", "tool:wiki_note_read"],
                         max_turns=12)
    return kernel, store, agent, ran


def _churn(n):
    """n steps of look-ups with different arguments each time (the repeat guard does not catch these)."""
    steps = []
    for i in range(n):
        if i % 2:
            steps.append([ToolCall(id=f"l{i}", name="wiki_note_list", arguments={"folder": f"folder-{i}"})])
        else:
            steps.append([ToolCall(id=f"s{i}", name="wiki_note_search", arguments={"query": f"weekly planning {i}"})])
    return steps


@pytest.mark.asyncio
async def test_stream_runs_at_most_four_lookups_then_answers():
    llm = ScriptLLM(_churn(7) + [REPLY])
    kernel, store, agent, ran = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="search the wiki")]
    end = [e for e in events if e.event_type == KernelEventType.TURN_END][-1]
    assert end.content == REPLY
    assert len(ran) == WIKI_LOOKUP_BUDGET == 4
    rows = [m for m in store.get_messages(session.id) if m.role == Role.TOOL]
    refused = [m for m in rows if m.content.startswith("Not run: you already looked in the wiki 4 times")]
    assert len(rows) == 7 and len(refused) == 3
    assert "Note:" not in end.content  # a refused look-up is not a failed tool


@pytest.mark.asyncio
async def test_run_turn_has_the_same_budget():
    llm = ScriptLLM(_churn(6) + [REPLY])
    kernel, store, agent, ran = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    msg = await kernel.run_turn(agent=agent, session_id=session.id, user_content="search the wiki")
    assert msg.content == REPLY
    assert len(ran) == 4


@pytest.mark.asyncio
async def test_other_wiki_tools_are_not_counted():
    steps = _churn(4) + [[ToolCall(id="r1", name="wiki_note_read", arguments={"path": "a.md"})],
                         [ToolCall(id="r2", name="wiki_note_read", arguments={"path": "b.md"})], REPLY]
    llm = ScriptLLM(steps)
    kernel, store, agent, ran = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    _ = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="read two notes")]
    assert [k for k, _ in ran].count("read") == 2 and len(ran) == 6


def test_budget_unit():
    b = WikiLookupBudget(budget=2)
    s = ToolCall(id="a", name="wiki_note_search", arguments={"query": "x"})
    assert b.check(s) is None and b.check(s) is None
    res = b.check(s)
    assert res.success and res.output.startswith("Not run:") and "no matching note was found" in res.output
    assert b.check(ToolCall(id="b", name="wiki_note_read", arguments={})) is None
    assert b.used == 2 and b.refused == 1


def test_search_and_list_descriptions_carry_the_hint():
    from pathlib import Path

    src = Path("src/application/skills/wiki_tools.py").read_text(encoding="utf-8")
    assert src.count("+ WIKI_LOOKUP_HINT") == 2
    assert "say plainly that no matching note was found" in WIKI_LOOKUP_HINT


@pytest.mark.asyncio
async def test_lookup_tools_are_not_offered_once_the_budget_is_used_up():
    llm = ScriptLLM(_churn(5) + [REPLY])
    kernel, store, agent, ran = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    _ = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="search the wiki")]
    offered = [sorted(t.name for t in (r.tools or [])) for r in llm.streams]
    assert "wiki_note_search" in offered[3] and "wiki_note_list" in offered[3]
    for names in offered[4:]:
        assert "wiki_note_search" not in names and "wiki_note_list" not in names
        assert "wiki_note_read" in names


@pytest.mark.asyncio
async def test_a_repeated_lookup_counts_against_the_budget():
    same = [ToolCall(id="s", name="wiki_note_search", arguments={"query": "weekly planning"})]
    steps = [same, [ToolCall(id="rep", name="wiki_note_search", arguments={"query": "weekly planning"})]] + _churn(3) + [REPLY]
    llm = ScriptLLM(steps)
    kernel, store, agent, ran = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    _ = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="search the wiki")]
    rows = [m.content for m in store.get_messages(session.id) if m.role == Role.TOOL]
    assert len(ran) == 3  # the repeat was answered from the earlier result but still used a look-up
    assert len(rows) == 5 and "already_done" in rows[1] and rows[-1].startswith("Not run:"), rows
