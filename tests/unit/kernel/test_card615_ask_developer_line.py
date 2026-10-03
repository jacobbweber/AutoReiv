"""CARD-615: the Ask Developer ending is added by the kernel only when a tool is truly missing.

- No agent's domain line tells the model to write the line.
- The line is added when a call was refused as an unknown tool / not the agent's and nothing else ran OK, or the
  reply turns the request down without any tool use (and does not point at another agent).
- After a rejection, an empty result or a successful tool call, the model's own copy is dropped.
"""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.agent_skills.allowed_tools import domain_line
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.repeat_guard import rejection_text
from src.application.kernel.reply_rules import ASK_DEVELOPER_LINE, ask_developer_ending
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_skills.catalog import platform_pack_profile

U = lambda text="do it": ChatMessage(role=Role.USER, content=text)  # noqa: E731
T = lambda content, name="t": ChatMessage(role=Role.TOOL, content=content, name=name)  # noqa: E731
MODEL_TAIL = "The note was not saved. You can use Ask Developer to add the wiki_note_create capability."


def test_domain_line_never_asks_for_the_line():
    for agent_id in ("autoreiv", "tutor", "toolsmith"):
        assert "Ask Developer" not in domain_line(platform_pack_profile(agent_id))


OWN = {"wiki_note_search", "wiki_note_create", "wiki_note_read"}


def test_rejected_write_drops_the_models_line():
    hist = [U(), T('{"hits": 2}', "wiki_note_search"), T(rejection_text("wiki_note_create"), "wiki_note_create")]
    out = ask_developer_ending("Here is the summary.\n\n" + MODEL_TAIL, hist, "save the note", OWN)
    assert "Ask Developer" not in out and out.endswith("The note was not saved.")


def test_resumed_reply_after_rejection_drops_it_too():
    # The resumed turn ran no tool itself; the rejection row since the user message still counts as tool use.
    hist = [U(), ChatMessage(role=Role.ASSISTANT, content=""), T(rejection_text("wiki_note_create"))]
    assert "Ask Developer" not in ask_developer_ending("Done.\n" + MODEL_TAIL, hist, None, OWN)


def test_empty_result_drops_it():
    hist = [U(), T('{"hits": []}', "wiki_note_search")]
    out = ask_developer_ending("The wiki has no gardening notes, so there is nothing to summarize.\n" + MODEL_TAIL, hist, None, OWN)
    assert "Ask Developer" not in out


def test_unknown_tool_with_nothing_else_ok_adds_the_exact_line():
    hist = [U("send a fax"), T("Tool Error: Tool 'send_fax' not found in system registry.", "send_fax")]
    out = ask_developer_ending("I could not send the fax: there is no fax tool.", hist, None, OWN)
    assert out.endswith("\n\n" + ASK_DEVELOPER_LINE) and out.count("Ask Developer") == 1


def test_unknown_tool_then_a_good_call_adds_nothing():
    hist = [U(), T("Tool Error: Tool 'wiki_find' not found in system registry."), T('{"hits": 1}', "wiki_note_search")]
    assert ask_developer_ending("Found one note.", hist, None, OWN) == "Found one note."


def test_partly_done_with_a_missing_capability_gets_the_line():
    hist = [U("summarize gardening and email it"), T('{"hits": 2}', "wiki_note_search")]
    reply = "Here is the summary. I don't have a tool to send email, so I could not email it."
    out = ask_developer_ending(reply, hist, "send email, so I could not email it", OWN)
    assert out == reply + "\n\n" + ASK_DEVELOPER_LINE


def test_a_gap_about_the_agents_own_tool_adds_nothing():
    hist = [U(), T('{"hits": 2}', "wiki_note_search")]
    reply = "I cannot create the note: I do not have the tool wiki_note_create available. " + MODEL_TAIL
    out = ask_developer_ending(reply, hist, "wiki_note_create available", OWN)
    assert "Ask Developer" not in out


def test_turn_down_without_tools_gets_one_line():
    out = ask_developer_ending("I can't book flights; no agent covers that. You can use Ask Developer to add this.",
                               [U("book a flight")], None, OWN)
    assert out == "I can't book flights; no agent covers that.\n\n" + ASK_DEVELOPER_LINE
    out = ask_developer_ending("I don't have a tool to send faxes.", [U("send a fax")], "send faxes", OWN)
    assert out.endswith(ASK_DEVELOPER_LINE)


def test_no_agent_covers_wording_gets_the_line():
    out = ask_developer_ending("No agent covers sending faxes.", [U("send a fax")], None, OWN)
    assert out == "No agent covers sending faxes.\n\n" + ASK_DEVELOPER_LINE
    assert "No agent covers" in domain_line(platform_pack_profile("autoreiv"))


def test_toolsmith_never_gets_the_line():
    hist = [U("send a fax"), T("Tool Error: Tool 'send_fax' not found in system registry.")]
    assert ask_developer_ending("No agent covers faxes.", hist, "faxes", OWN, offer=False) == "No agent covers faxes."
    assert "Ask Developer" not in ask_developer_ending("Saved. " + MODEL_TAIL, [U()], None, OWN, offer=False)


def test_pointing_at_another_agent_is_not_a_turn_down():
    out = ask_developer_ending("I can't make flashcards here; open Tutor in Chat.", [U("flashcards")], "make flashcards", OWN)
    assert "Ask Developer" not in out


def test_a_plain_answer_is_untouched():
    assert ask_developer_ending("Paris.", [U("capital of France?")], None, OWN) == "Paris."


def test_only_the_ask_developer_sentence_goes():
    hist = [U(), T('{"ok": true}', "wiki_note_search")]
    out = ask_developer_ending("Saved nothing. Use **Ask Developer** if you want a new tool. Anything else is done.", hist, None, OWN)
    assert out == "Saved nothing. Anything else is done."


# ---------------------------------------------------------------- end to end through stream_turn


class ToolThenTailLLM(LLMProviderPort):
    provider_id = "mock"

    def __init__(self, first_tool: str):
        self.first_tool, self.calls = first_tool, 0

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(model=request.model, finish_reason="stop",
                                  message=ChatMessage(role=Role.ASSISTANT, content="ok"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.calls += 1
        if self.calls == 1:
            yield StreamChunk(tool_calls=[ToolCall(id="c1", name=self.first_tool, arguments={})],
                              is_finished=True, finish_reason="tool_calls")
        else:
            yield StreamChunk(content="I looked. " + MODEL_TAIL)
            yield StreamChunk(is_finished=True, finish_reason="stop")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


async def _run(first_tool: str) -> List[str]:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    reg = ScopedToolRegistry()
    reg.register_tool(name="note_search", description="s", handler=lambda: {"hits": []},
                      parameters={"type": "object", "properties": {}})
    gw = MultiProviderGateway()
    gw.register_provider(ToolThenTailLLM(first_tool))
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:note_search"], max_turns=4)
    sid = store.create_session(agent_id=agent.id, title="t").id
    end = None
    async for ev in kernel.stream_turn(agent, sid, user_content="Find gardening notes"):
        if ev.event_type == KernelEventType.TURN_END:
            end = ev.content
    saved = [m.content for m in store.get_messages(session_id=sid) if m.role == Role.ASSISTANT and m.content]
    return [end or "", saved[-1] if saved else ""]


@pytest.mark.asyncio
async def test_stream_turn_saves_the_reply_without_the_models_line_after_its_tool_ran():
    end, saved = await _run("note_search")
    assert "Ask Developer" not in saved and "Ask Developer" not in end
    assert saved.startswith("I looked.")


@pytest.mark.asyncio
async def test_stream_turn_adds_the_line_when_the_tool_does_not_exist():
    end, saved = await _run("send_fax")
    assert saved.endswith(ASK_DEVELOPER_LINE) and saved.count("Ask Developer") == 1
