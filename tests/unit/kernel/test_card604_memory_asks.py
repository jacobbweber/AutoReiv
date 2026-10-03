"""CARD-604: memory asks in multi-part Chat requests.

- The rule and the memorize_fact description say a request to remember needs the tool call in the same reply.
- When the CARD-599 check finds a memory ask not done, the kernel gives the model one more step to call
  memorize_fact; "Not done" is appended only if it still did not save.
- A "Not done" line for a memory part whose tool did run (checker false positive) is dropped.
"""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.reply_rules import (
    REPLY_RULES_BLOCK,
    drop_false_not_done,
    memory_not_done_lines,
    memory_retry_prompt,
    parts_check_prompt,
    settle_memory_retry,
)
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

MULTI = "Remember that my token is teal, tell me the session ID, list the agents, and read README.md."
REPLY = "The session ID is s-1. README.md says hello."
NOT_DONE_MEMORY = "Not done: Remember that my token is teal."


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


def _kernel(llm, *, offer_memorize=True):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    saved = []
    reg = ScopedToolRegistry()
    if offer_memorize:
        reg.register_tool(name="memorize_fact", description="m",
                          handler=lambda entity, attribute, value: saved.append(value) or {"status": "ADD"},
                          parameters={"type": "object", "properties": {"entity": {"type": "string"},
                                      "attribute": {"type": "string"}, "value": {"type": "string"}}})
    reg.register_tool(name="recall_agent_memory", description="r", handler=lambda query: {"facts": []},
                      parameters={"type": "object", "properties": {"query": {"type": "string"}}})
    reg.register_tool(name="read_file", description="f", handler=lambda path: {"text": "hello"},
                      parameters={"type": "object", "properties": {"path": {"type": "string"}}})
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    skills = ["tool:recall_agent_memory", "tool:read_file", "tool:memorize_fact"]
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=skills, max_turns=8)
    return kernel, store, agent, saved


def _read(i=1):
    return [ToolCall(id=f"r{i}", name="read_file", arguments={"path": "README.md"})]


def _memorize(i=1):
    return [ToolCall(id=f"m{i}", name="memorize_fact", arguments={"entity": "user", "attribute": "token", "value": "teal"})]


async def _stream(kernel, store, agent, text=MULTI):
    session = store.create_session(agent_id=agent.id, title="t")
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content=text,
                                                  parts_request=text)]
    ends = [e for e in events if e.event_type == KernelEventType.TURN_END]
    assert len(ends) == 1
    tokens = "".join(e.content for e in events if e.event_type == KernelEventType.TOKEN)
    return ends[0].content, tokens, store.get_messages(session.id)


@pytest.mark.asyncio
async def test_skipped_memory_ask_gets_one_step_to_save_and_no_not_done_line():
    llm = ScriptLLM([_read(), REPLY, _memorize(), "Saved: your token is teal."], check_answer=NOT_DONE_MEMORY)
    kernel, store, agent, saved = _kernel(llm)
    end, tokens, rows = await _stream(kernel, store, agent)
    assert saved == ["teal"]
    assert end == "Saved: your token is teal."
    assert "Not done" not in tokens
    assert REPLY in tokens and tokens.index(REPLY) < tokens.index("Saved: your token is teal.")
    retry_req = llm.streams[2]
    assert "(AutoReiv check)" in retry_req.messages[-1].content and "memorize_fact" in retry_req.messages[-1].content
    contents = [r.content for r in rows if r.role == Role.ASSISTANT and r.content]
    assert contents == [REPLY, "Saved: your token is teal."]
    assert all("(AutoReiv check)" not in (r.content or "") for r in rows)  # the nudge is never saved
    assert len([c for c in llm.completes if c.tools is None]) == 1  # one check, not re-run after the retry


@pytest.mark.asyncio
async def test_retry_without_a_save_still_names_the_part():
    llm = ScriptLLM([_read(), REPLY, "Sorry, I could not."], check_answer=NOT_DONE_MEMORY)
    kernel, store, agent, saved = _kernel(llm)
    end, _, _ = await _stream(kernel, store, agent)
    assert saved == []
    assert end == f"Sorry, I could not.\n\n{NOT_DONE_MEMORY}"


@pytest.mark.asyncio
async def test_other_not_done_lines_stay_after_the_memory_retry():
    llm = ScriptLLM([_read(), REPLY, _memorize(), "Saved."], check_answer=f"{NOT_DONE_MEMORY}\nNot done: list the agents.")
    kernel, store, agent, saved = _kernel(llm)
    end, _, _ = await _stream(kernel, store, agent)
    assert saved == ["teal"]
    assert end == "Saved.\n\nNot done: list the agents."


@pytest.mark.asyncio
async def test_no_retry_when_memorize_fact_is_not_offered():
    llm = ScriptLLM([_read(), REPLY], check_answer=NOT_DONE_MEMORY)
    kernel, store, agent, _ = _kernel(llm, offer_memorize=False)
    end, _, _ = await _stream(kernel, store, agent)
    assert end == f"{REPLY}\n\n{NOT_DONE_MEMORY}"


@pytest.mark.asyncio
async def test_checker_false_positive_for_a_recall_that_ran_is_dropped():
    recall = [ToolCall(id="c1", name="recall_agent_memory", arguments={"query": "test token"})]
    text = "Recall my test token from memory, tell me the session ID, and read README.md."
    llm = ScriptLLM([recall, REPLY], check_answer="Done: session ID - answered\nNot done: Recall test token memory.")
    kernel, store, agent, _ = _kernel(llm)
    end, _, _ = await _stream(kernel, store, agent, text)
    assert end == REPLY


def test_helpers():
    ran_ok = ["recall_agent_memory(query=x) ok", "memorize_fact(entity=user) ok"]
    assert drop_false_not_done("Not done: Recall test token memory.", ran_ok) == ""
    assert drop_false_not_done("Not done: Remember my harbor is Bar Harbor.", ran_ok) == ""
    assert drop_false_not_done("Not done: Recall test token memory.", ["recall_agent_memory(query=x) failed"]) == (
        "Not done: Recall test token memory.")
    assert drop_false_not_done("Not done: list the agents.", ran_ok) == "Not done: list the agents."
    lines = "Not done: Remember that my favorite harbor is Bar Harbor.\nNot done: list the agents."
    assert memory_not_done_lines(lines) == ["Not done: Remember that my favorite harbor is Bar Harbor."]
    assert memory_not_done_lines("Not done: Recall what you remember about me.") == []
    assert "Remember that my favorite harbor is Bar Harbor" in memory_retry_prompt(memory_not_done_lines(lines))
    assert settle_memory_retry(lines, ["memorize_fact(value=Bar Harbor) ok"]) == "Not done: list the agents."
    assert settle_memory_retry(lines, []) == lines


def test_rule_and_descriptions_ask_for_the_call():
    from pathlib import Path

    assert "memorize_fact in the same reply" in REPLY_RULES_BLOCK
    desc = Path("src/application/memory/agent_memory_tools.py").read_text(encoding="utf-8")
    assert "call this in the same reply" in desc
    prompt = parts_check_prompt(MULTI, ["recall_agent_memory(query=x) ok"], REPLY)
    assert "recalling or looking up memory is done by recall_agent_memory" in prompt
    assert "recalling something is not remembering it" not in prompt
