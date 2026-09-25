"""CARD-475: an empty model reply is an error, never a saved empty row.

[REQ-475-004] stream_turn sends an error event and run_turn raises; neither saves
an assistant row with no content and no tool calls.
[REQ-475-006] history replay skips empty assistant rows already in the DB.
The kernel forwards the gateway's attachment notice once per turn.
"""

from __future__ import annotations

import base64
from typing import AsyncIterator, List

import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.model_capabilities import ModelCapabilityResolver
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.errors import EmptyModelReplyError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.domain.kernel.models import AgentProfile, KernelEventType
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class ScriptedLLM(LLMProviderPort):
    provider_id = "mock"

    def __init__(self, stream_chunks=None, responses=None):
        self.stream_chunks = list(stream_chunks or [])
        self.responses = list(responses or [])
        self.requests: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if self.responses:
            return self.responses.pop(0)
        return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content="fine"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        chunks = self.stream_chunks.pop(0) if self.stream_chunks else [
            StreamChunk(content="fine", is_finished=True, finish_reason="stop")
        ]
        for c in chunks:
            yield c

    async def list_models(self):
        return []


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


def _kernel(store, llm) -> AgentKernel:
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    gw.set_capability_resolver(ModelCapabilityResolver(settings_getter=lambda k, d=None: d))
    return AgentKernel(
        gateway=gw,
        tool_registry=ScopedToolRegistry(),
        state_store=store,
        telemetry=TelemetryCollector(store=store),
    )


def _profile() -> AgentProfile:
    return AgentProfile(
        id="general-assistant",
        name="General Assistant",
        description="Daily assistant",
        system_prompt="You are helpful.",
        allowed_tool_names=[],
    )


def _assistant_rows(store, session_id):
    return [m for m in store.get_messages(session_id=session_id) if m.role == Role.ASSISTANT]


@pytest.mark.asyncio
async def test_stream_turn_empty_reply_sends_error_and_saves_no_row(store):
    llm = ScriptedLLM(stream_chunks=[[StreamChunk(content="", is_finished=True, finish_reason="stop")]])
    kernel = _kernel(store, llm)
    session = store.create_session(agent_id="general-assistant", title="empty")
    events = [e async for e in kernel.stream_turn(_profile(), session.id, "hello")]

    errors = [e for e in events if e.event_type == KernelEventType.ERROR]
    assert errors and "empty reply" in errors[-1].content.lower()
    assert not [e for e in events if e.event_type == KernelEventType.TURN_END]
    assert _assistant_rows(store, session.id) == []


@pytest.mark.asyncio
async def test_run_turn_empty_reply_raises_and_saves_no_row(store):
    llm = ScriptedLLM(
        responses=[CompletionResponse(model="mock/m", message=ChatMessage(role=Role.ASSISTANT, content=""))]
    )
    kernel = _kernel(store, llm)
    session = store.create_session(agent_id="general-assistant", title="empty-run")
    with pytest.raises(EmptyModelReplyError):
        await kernel.run_turn(agent=_profile(), session_id=session.id, user_content="hello")
    assert _assistant_rows(store, session.id) == []


@pytest.mark.asyncio
async def test_stream_turn_history_skips_empty_assistant_rows(store):
    llm = ScriptedLLM()
    kernel = _kernel(store, llm)
    session = store.create_session(agent_id="general-assistant", title="poisoned")
    store.save_message(session_id=session.id, agent_id="general-assistant",
                       message=ChatMessage(role=Role.USER, content="first"))
    store.save_message(session_id=session.id, agent_id="general-assistant",
                       message=ChatMessage(role=Role.ASSISTANT, content=""))
    events = [e async for e in kernel.stream_turn(_profile(), session.id, "Hi")]

    assert [e for e in events if e.event_type == KernelEventType.TURN_END]
    sent = llm.requests[0].messages
    assert not [m for m in sent if m.role == Role.ASSISTANT and not (m.content or "").strip() and not m.tool_calls]
    assert sent[-1].content == "Hi"


@pytest.mark.asyncio
async def test_run_turn_history_skips_empty_assistant_rows(store):
    llm = ScriptedLLM()
    kernel = _kernel(store, llm)
    session = store.create_session(agent_id="general-assistant", title="poisoned-run")
    store.save_message(session_id=session.id, agent_id="general-assistant",
                       message=ChatMessage(role=Role.USER, content="first"))
    store.save_message(session_id=session.id, agent_id="general-assistant",
                       message=ChatMessage(role=Role.ASSISTANT, content=""))
    msg = await kernel.run_turn(agent=_profile(), session_id=session.id, user_content="Hi")
    assert msg.content == "fine"
    sent = llm.requests[0].messages
    assert not [m for m in sent if m.role == Role.ASSISTANT and not (m.content or "").strip() and not m.tool_calls]


@pytest.mark.asyncio
async def test_stream_turn_forwards_attachment_notice(store, tmp_path):
    png = tmp_path / "abc_shot.png"
    png.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    ))
    content = f"what is this?\n*(Attached Image: `shot.png`, 68 bytes, format: `image/png`, Local Path: `{png}`)*"
    llm = ScriptedLLM()
    kernel = _kernel(store, llm)
    session = store.create_session(agent_id="general-assistant", title="notice")
    events = [e async for e in kernel.stream_turn(_profile(), session.id, content)]

    notices = [e for e in events if e.event_type == KernelEventType.NOTICE]
    assert len(notices) == 1
    assert "only saw the file name `shot.png`" in notices[0].content
    assert notices[0].notice["files"] == ["shot.png"]
    assert not any(m.images for m in llm.requests[0].messages)
    assert [e for e in events if e.event_type == KernelEventType.TURN_END]
