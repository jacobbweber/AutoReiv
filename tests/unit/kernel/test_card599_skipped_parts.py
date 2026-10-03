"""CARD-599: a multi-part request must end with every part done or the skipped parts named.

(a) the platform rule is in the generated instructions (see test_card600_* for the prompt check);
(b) after the final reply to a 3+ part request, one short no-tools check on the same model appends
    "Not done: ..." lines for parts that were skipped. No model swap; single-part requests never pay for it.
"""

from __future__ import annotations

from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.reply_rules import needs_parts_check, parse_parts_check, parts_check_prompt, request_parts
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

MULTI = "Remember that my token is teal, tell me the session ID, list the agents, and read README.md."
REPLY = "Saved your token. The session ID is s-1. README.md says hello."


class CheckLLM(LLMProviderPort):
    """stream(): one tool call, then the reply. complete(): the skipped-parts checker's answer."""

    provider_id = "mock"

    def __init__(self, check_answer: str):
        self.check_answer = check_answer
        self.streams: List[CompletionRequest] = []
        self.completes: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.completes.append(request)
        return CompletionResponse(model=request.model, finish_reason="stop",
                                  message=ChatMessage(role=Role.ASSISTANT, content=self.check_answer))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.streams.append(request)
        if len(self.streams) == 1:
            yield StreamChunk(tool_calls=[ToolCall(id="m1", name="memorize", arguments={"fact": "token teal"})],
                              is_finished=True, finish_reason="tool_calls")
        else:
            yield StreamChunk(content=REPLY)
            yield StreamChunk(is_finished=True, finish_reason="stop")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


def _kernel(llm):
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    reg = ScopedToolRegistry()
    reg.register_tool(name="memorize", description="m", handler=lambda fact: {"saved": fact},
                      parameters={"type": "object", "properties": {"fact": {"type": "string"}}})
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:memorize"], max_turns=5)
    return kernel, store, agent


async def _stream(kernel, store, agent, text, check=True):
    session = store.create_session(agent_id=agent.id, title="t")
    events = [e async for e in kernel.stream_turn(agent=agent, session_id=session.id, user_content=text,
                                                  parts_request=text if check else None)]
    end = [e for e in events if e.event_type == KernelEventType.TURN_END][-1]
    tokens = "".join(e.content for e in events if e.event_type == KernelEventType.TOKEN)
    return end.content, tokens, store.get_messages(session.id)


@pytest.mark.asyncio
async def test_skipped_part_is_named_at_the_end_of_the_reply():
    llm = CheckLLM("Thinking it over.\nNot done: list the agents.")
    kernel, store, agent = _kernel(llm)
    end, tokens, saved = await _stream(kernel, store, agent, MULTI)
    assert end == f"{REPLY}\n\nNot done: list the agents."
    assert tokens.endswith("Not done: list the agents.")
    assert saved[-1].content == end
    assert len(llm.completes) == 1
    check = llm.completes[0]
    assert check.tools is None and check.model == llm.streams[0].model  # same model, no tools
    prompt = check.messages[-1].content
    assert MULTI in prompt and REPLY in prompt and "memorize(fact=token teal) ok" in prompt


@pytest.mark.asyncio
async def test_all_done_leaves_the_reply_alone():
    llm = CheckLLM("ALL DONE")
    kernel, store, agent = _kernel(llm)
    end, _, _ = await _stream(kernel, store, agent, MULTI)
    assert end == REPLY


@pytest.mark.asyncio
async def test_single_part_request_makes_no_check_call():
    llm = CheckLLM("Not done: everything.")
    kernel, store, agent = _kernel(llm)
    end, _, _ = await _stream(kernel, store, agent, "Remember that my token is teal.")
    assert end == REPLY and llm.completes == []


@pytest.mark.asyncio
async def test_checker_failure_keeps_the_reply():
    class Broken(CheckLLM):
        async def complete(self, request):
            raise RuntimeError("checker down")

    kernel, store, agent = _kernel(Broken(""))
    end, _, _ = await _stream(kernel, store, agent, MULTI)
    assert end == REPLY


@pytest.mark.asyncio
async def test_only_chat_turns_that_pass_the_typed_text_are_checked():
    """Handoff children, phases, routines (run_turn) and resumes never pay for the check."""
    llm = CheckLLM("Not done: list the agents.")
    kernel, store, agent = _kernel(llm)
    end, _, _ = await _stream(kernel, store, agent, MULTI, check=False)
    assert end == REPLY and llm.completes == []

    class Batch(CheckLLM):
        async def complete(self, request):
            self.completes.append(request)
            return CompletionResponse(model=request.model, finish_reason="stop",
                                      message=ChatMessage(role=Role.ASSISTANT, content=REPLY))

    batch = Batch("unused")
    kernel, store, agent = _kernel(batch)
    session = store.create_session(agent_id=agent.id, title="t")
    msg = await kernel.run_turn(agent=agent, session_id=session.id, user_content=MULTI)
    assert msg.content == REPLY and len(batch.completes) == 1


def test_chat_short_turn_passes_the_typed_text():
    from pathlib import Path

    src = Path("src/web/routers/chat.py").read_text(encoding="utf-8")
    assert "parts_request=None if resume else req.content" in src


def test_part_counting_and_parsing():
    assert request_parts(MULTI) == 4
    assert request_parts("Hi, how are you?") < 3
    assert request_parts("What is a monad?") == 1
    assert request_parts("1. remember X\n2. recall Y\n3. read file Z") == 3
    assert needs_parts_check(MULTI, REPLY)
    assert not needs_parts_check(MULTI, "Done all but one; I skipped the agent list because no tool lists agents.")
    assert not needs_parts_check("What is a monad?", REPLY)
    assert parse_parts_check("ALL DONE") == ""
    assert parse_parts_check("- Not done: list agents\nnoise\nNot done: read README.md.") == (
        "Not done: list agents.\nNot done: read README.md.")
    assert "- none" in parts_check_prompt(MULTI, [], REPLY)
