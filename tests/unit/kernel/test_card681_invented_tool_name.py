"""CARD-681: a call to an invented tool name (wiki_template_search) is refused with the closest real names, the
next model call recovers with a real tool, and it is not treated as a missing capability (no gap, no Ask
Developer line). A name with no close real tool is still a truly missing tool (CARD-615 unchanged)."""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.reply_rules import ask_developer_ending, near_miss_tool_names
from src.application.kernel.tool_registry import (
    NEAR_MISS_TOOL_NAME,
    NO_SUCH_TOOL,
    ScopedToolRegistry,
    tool_not_offered_error,
)
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

OFFERED = {"wiki_template_list", "wiki_template_read", "wiki_note_search", "wiki_note_read"}
GIVE_UP_REPLY = "I don't have a wiki_template_search tool, so I could not search the templates."
INVENTED_REPLY = "There is no wiki_template_search tool, so I used wiki_template_list instead: one summary template."


def test_invented_name_is_refused_with_the_closest_real_names():
    text = tool_not_offered_error("wiki_template_search", OFFERED, exists=False)
    assert NEAR_MISS_TOOL_NAME in text
    assert "wiki_template_list" in text and "wiki_template_read" in text
    assert NO_SUCH_TOOL not in text  # not a missing capability


def test_a_name_with_no_close_real_tool_is_still_missing():
    text = tool_not_offered_error("send_fax", OFFERED, exists=False)
    assert NO_SUCH_TOOL in text and NEAR_MISS_TOOL_NAME not in text


def test_near_miss_names_are_read_from_this_turns_rows():
    rows = [ChatMessage(role=Role.USER, content="find the template"),
            ChatMessage(role=Role.TOOL, name="wiki_template_search",
                        content="Tool Error: " + tool_not_offered_error("wiki_template_search", OFFERED, exists=False))]
    assert near_miss_tool_names(rows) == {"wiki_template_search"}


def test_no_ask_developer_line_after_an_invented_name():
    hist = [ChatMessage(role=Role.USER, content="find the template"),
            ChatMessage(role=Role.TOOL, name="wiki_template_search",
                        content="Tool Error: " + tool_not_offered_error("wiki_template_search", OFFERED, exists=False))]
    out = ask_developer_ending("I could not find a template search tool.", hist, None, OFFERED)
    assert "Ask Developer" not in out


class InventThenRecoverLLM(LLMProviderPort):
    provider_id = "mock"

    def __init__(self, recover: bool = True, give_up: str = ""):
        self.requests: List[CompletionRequest] = []
        self.recover = recover
        self.give_up = give_up or GIVE_UP_REPLY

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(model=request.model, finish_reason="stop",
                                  message=ChatMessage(role=Role.ASSISTANT, content="ok"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        n = len(self.requests)
        if n == 1:
            yield StreamChunk(tool_calls=[ToolCall(id="c1", name="wiki_template_search", arguments={"query": "summary"})],
                              is_finished=True, finish_reason="tool_calls")
        elif n == 2 and self.recover:
            yield StreamChunk(tool_calls=[ToolCall(id="c2", name="wiki_template_list", arguments={})],
                              is_finished=True, finish_reason="tool_calls")
        else:
            yield StreamChunk(content=INVENTED_REPLY if self.recover else self.give_up)
            yield StreamChunk(is_finished=True, finish_reason="stop")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


async def _run(recover: bool, give_up: str = ""):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    reg = ScopedToolRegistry()
    ran = []
    for name in ("wiki_template_list", "wiki_template_read"):
        reg.register_tool(name=name, description=name, parameters={"type": "object", "properties": {}},
                          handler=(lambda n=name: ran.append(n) or [{"slug": "summary"}]))
    gw = MultiProviderGateway()
    llm = InventThenRecoverLLM(recover, give_up)
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:wiki_template_list", "tool:wiki_template_read"], max_turns=5)
    sid = store.create_session(agent_id=agent.id, title="t").id
    async for _ev in kernel.stream_turn(agent, sid, user_content="Find my summary template"):
        pass
    saved = [m.content for m in store.get_messages(session_id=sid) if m.role == Role.ASSISTANT and m.content]
    gaps = kernel.capability_gap_repo.list_gaps(agent_id="autoreiv", status=None)
    return llm, ran, saved[-1], gaps


@pytest.mark.asyncio
async def test_stream_turn_recovers_and_files_no_gap():
    llm, ran, saved, gaps = await _run(recover=True)
    refusal = [m.content for m in llm.requests[1].messages if m.role == Role.TOOL][-1]
    assert "wiki_template_list" in refusal and NEAR_MISS_TOOL_NAME in refusal
    assert ran == ["wiki_template_list"]  # recovered with the real tool
    assert saved.startswith("There is no wiki_template_search tool") and "Ask Developer" not in saved
    assert gaps == []


@pytest.mark.asyncio
async def test_giving_up_on_an_invented_name_is_not_a_capability_gap():
    _llm, ran, saved, gaps = await _run(recover=False)
    assert ran == []
    assert "Ask Developer" not in saved
    assert gaps == []


@pytest.mark.asyncio
async def test_giving_up_in_plain_words_is_not_a_gap_either():
    _llm, _ran, saved, gaps = await _run(recover=False, give_up="I don't have a template search tool, so I stopped.")
    assert "Ask Developer" not in saved
    assert gaps == []


@pytest.mark.asyncio
async def test_a_truly_missing_tool_still_gets_the_line():
    from tests.unit.kernel.test_card615_ask_developer_line import _run as run615

    _end, saved = await run615("send_fax")
    assert saved.endswith("You can use Ask Developer to add this.")
