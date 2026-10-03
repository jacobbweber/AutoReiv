"""CARD-600 (CARD-523 items 5 and 7) and the CARD-599 platform rule.

- ask_clarification ends the turn: no further model or tool calls, the question is the reply.
- A turn whose last failed tool call is not mentioned in the final reply gets one line:
  "Note: <tool> failed: <short error>." A reply that mentions it does not.
"""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.reply_rules import (
    CLARIFICATION_SKIPPED_RESULT,
    REPLY_RULES_BLOCK,
    failed_tool_note,
    short_error,
    track_failure,
)
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.platform_primitives import PlatformPrimitiveTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

QUESTION = "Which harbor do you mean, north or south?"


class ScriptedLLM(LLMProviderPort):
    """Each step is either a list of ToolCalls or a reply text; stream() and complete() share the script."""

    provider_id = "mock"

    def __init__(self, steps):
        self.steps = list(steps)
        self.requests: List[CompletionRequest] = []

    def _next(self, request):
        self.requests.append(request)
        assert self.steps, "the kernel made a model call the script did not expect"
        return self.steps.pop(0)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        step = self._next(request)
        if isinstance(step, str):
            return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content=step),
                                      finish_reason="stop")
        return CompletionResponse(model=request.model, finish_reason="tool_calls",
                                  message=ChatMessage(role=Role.ASSISTANT, content="", tool_calls=step))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        step = self._next(request)
        if isinstance(step, str):
            yield StreamChunk(content=step)
            yield StreamChunk(is_finished=True, finish_reason="stop")
        else:
            yield StreamChunk(tool_calls=step, is_finished=True, finish_reason="tool_calls")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


def _kernel(llm, *, tide_fails_times: int = 0):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    calls = []

    def harbor_tide(harbor):
        calls.append(harbor)
        if len(calls) <= tide_fails_times:
            raise RuntimeError("tide service down (HTTP 503)")
        return {"harbor": harbor, "high_tide": "14:05"}

    reg = ScopedToolRegistry()
    reg.register_tool(name="harbor_tide", description="tide", handler=harbor_tide,
                      parameters={"type": "object", "properties": {"harbor": {"type": "string"}}})
    PlatformPrimitiveTools(state_store=store).register_tools(reg)
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:harbor_tide", "tool:ask_clarification"], max_turns=6)
    return kernel, store, agent, calls


def _tide(i=1, harbor="north"):
    return ToolCall(id=f"t{i}", name="harbor_tide", arguments={"harbor": harbor})


def _ask(i=1):
    return ToolCall(id=f"q{i}", name="ask_clarification", arguments={"question": QUESTION})


async def _stream(kernel, store, agent, text="When is high tide?"):
    session = store.create_session(agent_id=agent.id, title="t")
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content=text)]
    return events, store.get_messages(session.id), session


def _end(events):
    ends = [e for e in events if e.event_type == KernelEventType.TURN_END]
    assert len(ends) == 1
    return ends[0]


# ---------------- item 5: ask_clarification ends the turn ----------------


@pytest.mark.asyncio
async def test_stream_clarification_stops_the_loop_and_shows_the_question():
    llm = ScriptedLLM([[_ask(), _tide()], "should never be asked for"])
    kernel, store, agent, calls = _kernel(llm)
    events, saved, _ = await _stream(kernel, store, agent)
    assert len(llm.requests) == 1, "no further model call after ask_clarification"
    assert calls == [], "a tool call after ask_clarification in the same step is not run"
    assert _end(events).content == QUESTION
    tokens = "".join(e.content for e in events if e.event_type == KernelEventType.TOKEN)
    assert QUESTION in tokens
    assert saved[-1].role == Role.ASSISTANT and saved[-1].content == QUESTION
    skipped = [m for m in saved if m.role == Role.TOOL and m.tool_call_id == "t1"]
    assert skipped and skipped[0].content == CLARIFICATION_SKIPPED_RESULT  # every call still has its result
    assert not [e for e in events if e.event_type == KernelEventType.TOOL_START and e.tool_call["name"] == "harbor_tide"]


@pytest.mark.asyncio
async def test_stream_next_user_message_answers_the_question():
    llm = ScriptedLLM([[_ask()], [_tide(2, "south")], "High tide in the south harbor is at 14:05."])
    kernel, store, agent, calls = _kernel(llm)
    _, _, session = await _stream(kernel, store, agent)
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content="South.")]
    assert calls == ["south"]
    assert _end(events).content == "High tide in the south harbor is at 14:05."
    second_turn_messages = llm.requests[1].messages
    assert any(m.role == Role.ASSISTANT and m.content == QUESTION for m in second_turn_messages)
    assert second_turn_messages[-1].role == Role.USER and second_turn_messages[-1].content == "South."


@pytest.mark.asyncio
async def test_stream_question_already_written_is_not_repeated():
    class WritesQuestion(ScriptedLLM):
        async def stream(self, request):
            self._next(request)
            yield StreamChunk(content=QUESTION)
            yield StreamChunk(tool_calls=[_ask()], is_finished=True, finish_reason="tool_calls")

    llm = WritesQuestion([None])
    kernel, store, agent, _ = _kernel(llm)
    events, saved, _ = await _stream(kernel, store, agent)
    tokens = "".join(e.content for e in events if e.event_type == KernelEventType.TOKEN)
    assert tokens.count(QUESTION) == 1
    assert sum(1 for m in saved if m.role == Role.ASSISTANT and QUESTION in (m.content or "")) == 1


@pytest.mark.asyncio
async def test_run_turn_clarification_stops_the_loop():
    llm = ScriptedLLM([[_ask(), _tide()], "should never be asked for"])
    kernel, store, agent, calls = _kernel(llm)
    session = store.create_session(agent_id=agent.id, title="t")
    msg = await kernel.run_turn(agent=agent, session_id=session.id, user_content="When is high tide?")
    assert len(llm.requests) == 1 and calls == []
    assert msg.content == QUESTION
    assert store.get_messages(session.id)[-1].content == QUESTION


# ---------------- item 7: a hidden failed tool call gets a note ----------------


@pytest.mark.asyncio
async def test_stream_reply_that_hides_the_failure_gets_the_note():
    llm = ScriptedLLM([[_tide()], "High tide is at 14:05."])
    kernel, store, agent, _ = _kernel(llm, tide_fails_times=1)
    events, saved, _ = await _stream(kernel, store, agent)
    end = _end(events).content
    assert end.startswith("High tide is at 14:05.")
    note = end.splitlines()[-1]
    assert note.startswith("Note: harbor_tide failed: ") and "tide service down" in note and note.endswith(".")
    assert saved[-1].content == end
    tokens = "".join(e.content for e in events if e.event_type == KernelEventType.TOKEN)
    assert tokens.endswith(note)
    assert len(llm.requests) == 2, "no re-prompt for the note"


@pytest.mark.asyncio
async def test_stream_reply_that_mentions_the_failure_gets_no_note():
    llm = ScriptedLLM([[_tide()], "The tide lookup failed (service down), so I can't give the time right now."])
    kernel, store, agent, _ = _kernel(llm, tide_fails_times=1)
    events, saved, _ = await _stream(kernel, store, agent)
    assert "Note:" not in _end(events).content
    assert "Note:" not in saved[-1].content


@pytest.mark.asyncio
async def test_stream_failure_fixed_by_a_retry_gets_no_note():
    llm = ScriptedLLM([[_tide(1)], [_tide(2, "north ")], "High tide is at 14:05."])
    kernel, store, agent, calls = _kernel(llm, tide_fails_times=1)
    events, _, _ = await _stream(kernel, store, agent)
    assert len(calls) == 2
    assert _end(events).content == "High tide is at 14:05."


@pytest.mark.asyncio
async def test_run_turn_reply_that_hides_the_failure_gets_the_note():
    llm = ScriptedLLM([[_tide()], "High tide is at 14:05."])
    kernel, store, agent, _ = _kernel(llm, tide_fails_times=1)
    session = store.create_session(agent_id=agent.id, title="t")
    msg = await kernel.run_turn(agent=agent, session_id=session.id, user_content="When is high tide?")
    assert msg.content.splitlines()[-1].startswith("Note: harbor_tide failed: ")
    assert store.get_messages(session.id)[-1].content == msg.content


def test_note_rules():
    fail = ("handoff_to_agent", "Tool Error: handoff budget exhausted after 3 steps\nTraceback ...")
    assert failed_tool_note("Here is the plan.", fail) == "Note: handoff_to_agent failed: handoff budget exhausted after 3 steps."
    assert failed_tool_note("The handoff to agent hit its budget.", fail) == ""
    assert failed_tool_note("I was unable to reach the Developer.", fail) == ""
    assert failed_tool_note("Here is the plan.", None) == ""
    assert len(short_error("x" * 500)) <= 160
    # approval parks and the clarification stop are not failures; a later success of the same tool clears it
    assert track_failure(None, "write_card", False, "approval_required:abc") is None
    assert track_failure(None, "ask_clarification", False, "boom") is None
    last = track_failure(None, "harbor_tide", False, "down")
    assert last == ("harbor_tide", "down")
    assert track_failure(last, "other_tool", True, None) == last
    assert track_failure(last, "harbor_tide", True, None) is None


# ---------------- CARD-599: the platform rule is in the generated instructions ----------------


def test_system_prompt_carries_the_multi_part_rule():
    kernel, _, agent, _ = _kernel(ScriptedLLM([]))
    prompt = kernel._build_effective_system_message(agent).content
    assert REPLY_RULES_BLOCK in prompt
    assert "If the request has several parts, do each one. End by listing any part you did not do and why." in prompt
    assert prompt.index("## Your domain") < prompt.index("## Answering")
