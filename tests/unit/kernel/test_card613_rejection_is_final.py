"""CARD-613: a rejected approval is final for the reply, and a job step that asks a question is not done.

- The TOOL row after a rejection tells the model plainly not to call the tool again.
- In the resumed reply the rejected tool is not offered, and a call to it anyway is refused without running and
  without a new approval card (a self-correcting refusal, not a failure note).
- A job step whose turn ends with ask_clarification waits for the answer (phase queued, job open, journey
  ``waiting_answer``); the next chat message continues that step with the answer. A normal reply still completes.
- A job left parked after its card was decided without a resume (e.g. through the API) shows as stopped (Resume).
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, List
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.repeat_guard import REJECTED_PREFIX, RepeatGuard, rejected_tool_names, rejection_text
from src.application.kernel.reply_rules import counts_as_failure
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.orchestration.chat_job_binding import job_waiting_for_answer_on_session
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.kill_resume import job_stopped_by_operator, job_waiting_for_answer
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk, ToolCall
from src.domain.kernel.models import AgentProfile, KernelEvent, KernelEventType
from src.domain.orchestration.models import JobStatus, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import chat as chat_mod

# ---------------------------------------------------------------- the rejection result


def test_rejection_text_says_do_not_call_again():
    text = rejection_text("wiki_note_create")
    assert text.startswith(REJECTED_PREFIX)  # the chat still shows the row as Rejected
    assert "Do not call wiki_note_create again" in text and "say plainly what was not done" in text


def _rows(*pairs):
    out = []
    for role, content, name in pairs:
        out.append(ChatMessage(role=role, content=content, name=name))
    return out


def test_rejected_names_reset_at_the_next_user_message():
    hist = _rows((Role.USER, "write it", None), (Role.TOOL, rejection_text("wiki_note_create"), "wiki_note_create"))
    assert rejected_tool_names(hist) == {"wiki_note_create"}
    assert rejected_tool_names(hist + _rows((Role.USER, "try again", None))) == set()
    assert rejected_tool_names(_rows((Role.TOOL, "Rejected. Tool did not run.", "x"))) == {"x"}  # older rows too


def test_a_call_to_a_rejected_tool_is_refused_and_is_not_a_failure():
    guard = RepeatGuard({"wiki_note_create"})
    res = guard.reuse(ToolCall(id="c1", name="wiki_note_create", arguments={"title": "Other title"}))
    assert res is not None and res.success is False and "already rejected wiki_note_create" in res.error
    assert counts_as_failure(res.tool_name, res.success, res.error) is False
    assert RepeatGuard({"wiki_note_create"}).reuse(ToolCall(id="c2", name="wiki_search", arguments={})) is None


# ---------------------------------------------------------------- the resumed reply


class RetryLLM(LLMProviderPort):
    """First step calls the rejected tool again; the second step answers."""

    provider_id = "mock"

    def __init__(self):
        self.streams: List[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(model=request.model, finish_reason="stop",
                                  message=ChatMessage(role=Role.ASSISTANT, content="ok"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.streams.append(request)
        if len(self.streams) == 1:
            yield StreamChunk(tool_calls=[ToolCall(id="r2", name="note_create", arguments={"title": "B"})],
                              is_finished=True, finish_reason="tool_calls")
        else:
            yield StreamChunk(content="Here is the summary. Not saved: you rejected the note.")
            yield StreamChunk(is_finished=True, finish_reason="stop")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_resumed_reply_does_not_offer_or_run_the_rejected_tool():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    ran = []
    reg = ScopedToolRegistry()
    reg.register_tool(name="note_create", description="n", handler=lambda title: ran.append(title) or {"ok": True},
                      parameters={"type": "object", "properties": {"title": {"type": "string"}}})
    reg.register_tool(name="note_search", description="s", handler=lambda q="": {"hits": []},
                      parameters={"type": "object", "properties": {"q": {"type": "string"}}})
    llm = RetryLLM()
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    kernel = AgentKernel(gateway=gw, tool_registry=reg, state_store=store, telemetry=TelemetryCollector(store=store))
    agent = AgentProfile(id="autoreiv", name="A", description="d", system_prompt="s", model="mock/m",
                         allowed_skill=["tool:note_create", "tool:note_search"], max_turns=5)
    sid = store.create_session(agent_id=agent.id, title="t").id
    store.save_message(session_id=sid, agent_id=agent.id, message=ChatMessage(role=Role.USER, content="Summarize"))
    store.save_message(session_id=sid, agent_id=agent.id, message=ChatMessage(
        role=Role.ASSISTANT, content="", tool_calls=[ToolCall(id="r1", name="note_create", arguments={"title": "A"})]))
    store.save_message(session_id=sid, agent_id=agent.id, message=ChatMessage(
        role=Role.TOOL, content=rejection_text("note_create"), tool_call_id="r1", name="note_create"))

    events = [e async for e in kernel.stream_turn(agent=agent, session_id=sid, resume=True)]

    offered = {t.name for t in (llm.streams[0].tools or [])}
    assert "note_create" not in offered and "note_search" in offered
    assert ran == []  # the repeated call never ran
    assert not [e for e in events if e.event_type == KernelEventType.APPROVAL_REQUIRED]
    assert store.get_pending_approvals(session_id=sid) == []
    refused = [m for m in store.get_messages(sid) if m.role == Role.TOOL and m.tool_call_id == "r2"]
    assert refused and "already rejected note_create" in refused[0].content
    end = [e for e in events if e.event_type == KernelEventType.TURN_END][-1]
    assert "Note: note_create failed" not in end.content


# ---------------------------------------------------------------- hitl route writes the text


def test_rejecting_through_the_api_writes_the_rejection_text(tmp_path):
    from fastapi.testclient import TestClient

    from src.web.app import create_app
    from tests.unit.web.test_hitl_web_api import MockLLM

    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    gateway = MultiProviderGateway(default_provider_id="mock")
    gateway.register_provider(MockLLM())
    app = create_app(state_store=store, gateway_instance=gateway, wiki_path=str(tmp_path / "wiki"))
    with TestClient(app) as tc:
        store.create_session(agent_id="autoreiv", title="t", session_id="sess_613_api")
        appr = store.create_approval("sess_613_api", "autoreiv", "wiki_note_create",
                                     {"title": "T", "_tool_call_id": "call_613"})
        res = tc.post(f"/api/approvals/{appr}/decision", json={"decision": "REJECTED"})
        assert res.status_code == 200
    rows = [m for m in store.get_messages("sess_613_api") if m.role == Role.TOOL]
    assert rows and rows[-1].content == rejection_text("wiki_note_create")
    assert rows[-1].tool_call_id == "call_613"


# ---------------------------------------------------------------- job state


@pytest.fixture
def store(tmp_path):
    return SQLiteStateStore(db_path=str(tmp_path / "card613.db"))


@pytest.fixture
def orch(store):
    return JobPhaseOrchestrator(store)


def _job(orch, sid):
    return orch.create_job_with_phases(
        goal="search then summarize",
        session_id=sid,
        agent_id="assistant",
        phase_specs=[{"name": "Formulate", "success_rule": "plan"}, {"name": "Execute", "success_rule": "summary"}],
    )


class _Kernel:
    def __init__(self, react=None):
        self.react = react
        self.calls = []

    async def stream_turn(self, profile, session_id, user_content, **kw):
        self.calls.append((session_id, user_content, kw.get("resume")))
        yield KernelEvent(event_type=KernelEventType.TURN_END, content="Which title should I use?",
                          is_finished=True, react=self.react)


async def _bound(store, orch, job, phase, kernel):
    queue: asyncio.Queue = asyncio.Queue()
    out = await chat_mod._stream_turn_bound(
        queue=queue, kernel=kernel, orch=orch, store=store, reflexion_engine=None, profile=MagicMock(id="assistant"),
        session_id=f"{job.session_id}::phase::{phase.id}", user_content="go", approval_mode="ask", resume=False,
        job=job, phase=phase, self_verify=False,
    )
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    return out, events


@pytest.mark.asyncio
async def test_a_step_that_asks_waits_for_the_answer_and_is_not_done(store, orch):
    job = _job(orch, "sess_613_q")
    phase = orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    out, events = await _bound(store, orch, job, phase, _Kernel(react={"clarification": True}))
    assert out == "question"
    assert store.get_phase(phase.id).status == PhaseStatus.QUEUED
    fresh = store.get_job(job.id)
    assert fresh.status == JobStatus.RUNNING and fresh.current_phase_id == phase.id
    assert job_waiting_for_answer(store, fresh) is True
    assert job_stopped_by_operator(store, fresh) is False  # not "stopped": the answer continues it
    assert job_waiting_for_answer_on_session(store, "sess_613_q").id == job.id
    assert any('"status": "waiting_for_answer"' in e for e in events)
    assert not any('"status": "done"' in e for e in events)


@pytest.mark.asyncio
async def test_a_normal_final_reply_still_completes_the_step(store, orch):
    job = _job(orch, "sess_613_done")
    phase = orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    out, _ = await _bound(store, orch, job, phase, _Kernel(react=None))
    assert out == "done"
    assert store.get_phase(phase.id).status == PhaseStatus.DONE
    assert job_waiting_for_answer(store, store.get_job(job.id)) is False


def _app(store, orch, kernel):
    app = FastAPI()
    app.include_router(chat_mod.router)
    registry = MagicMock()
    registry.get_profile.return_value = AgentProfile(
        id="assistant", name="Assistant", description="d", system_prompt="", max_turns=5
    )
    app.state.registry = registry
    app.state.kernel = kernel
    app.state.job_orchestrator = orch
    app.state.reflexion_engine = None
    app.state.store = store
    tel = MagicMock()
    app.state.telemetry = tel
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.mark.asyncio
async def test_the_next_chat_message_answers_the_waiting_step(store, orch):
    sid = "sess_613_answer"
    store.create_session(agent_id="assistant", title="t", session_id=sid)
    job = _job(orch, sid)
    phase = orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    store.create_session(agent_id="assistant", title="Formulate", session_id=f"{sid}::phase::{phase.id}")
    orch.wait_for_answer(phase.id)
    kernel = _Kernel(react={"clarification": True})  # it asks again, so the job keeps waiting
    async with _app(store, orch, kernel) as c:
        journey = (await c.get(f"/api/chat/sessions/{sid}/journey")).json()
        assert journey["jobs"][0]["waiting_answer"] is True and journey["jobs"][0]["stopped"] is False
        res = await c.post("/api/chat/stream", json={"agent_id": "assistant", "session_id": sid, "content": "Use Roses"})
        body = res.text
    assert kernel.calls and kernel.calls[0] == (f"{sid}::phase::{phase.id}", "Use Roses", False)
    assert [m.content for m in store.get_messages(sid) if m.role == Role.USER][-1] == "Use Roses"
    assert "waiting_answer" in body
    assert job_waiting_for_answer(store, store.get_job(job.id)) is True


def test_a_job_left_parked_after_a_decision_shows_stopped(store, orch):
    sid = "sess_613_parked"
    job = _job(orch, sid)
    phase = orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    orch.park_phase(phase.id)
    appr = store.create_approval(f"{sid}::phase::{phase.id}", "assistant", "wiki_note_create", {"title": "T"})
    assert job_stopped_by_operator(store, store.get_job(job.id)) is False  # the card is still pending
    store.resolve_approval(appr, "rejected")
    assert job_stopped_by_operator(store, store.get_job(job.id)) is True  # decided, nothing resumed: Resume shows
    orch.start_phase(phase.id)
    assert job_stopped_by_operator(store, store.get_job(job.id)) is False


def test_rejection_rows_parse_as_json_safe_strings():
    assert json.dumps(rejection_text("x"))  # plain text, no JSON needed by the chat row renderer
