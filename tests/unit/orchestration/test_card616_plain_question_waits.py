"""CARD-616: a job step whose final reply asks a plain-text question waits for the answer."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.kill_resume import job_waiting_for_answer
from src.application.orchestration.plain_question import ends_with_question, reply_needs_answer
from src.domain.gateway.models import ChatMessage, CompletionResponse, Role
from src.domain.kernel.models import KernelEvent, KernelEventType
from src.domain.orchestration.models import JobStatus, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import chat as chat_mod

ASKS = "I found two notes on tomatoes.\n\nShould I save the summary under 00_Inbox or 01_Notes?"
OFFERS = "Saved the note to 00_Inbox/tomatoes.md.\n\nAnything else?"


class _Gateway:
    default_model_id = "vllm/default"

    def __init__(self, answer="yes", fail=False):
        self.answer, self.fail, self.requests = answer, fail, []

    async def complete(self, req):
        self.requests.append(req)
        if self.fail:
            raise RuntimeError("down")
        return CompletionResponse(model=req.model, message=ChatMessage(role=Role.ASSISTANT, content=self.answer))


def test_only_a_last_line_ending_in_a_question_mark_is_checked():
    assert ends_with_question(ASKS)
    assert ends_with_question("Which title should I use?**\n\n")
    assert not ends_with_question("Done. Is it ok? I saved it anyway.")
    assert not ends_with_question("")


@pytest.mark.asyncio
async def test_check_uses_the_given_model_with_no_tools():
    gw = _Gateway("Yes.")
    assert await reply_needs_answer(gw, "vllm/nemotron-3.5-lightning", ASKS, task="write a tomato note") is True
    req = gw.requests[0]
    assert req.model == "vllm/nemotron-3.5-lightning" and not req.tools and req.background
    assert "write a tomato note" in req.messages[1].content


@pytest.mark.asyncio
async def test_no_answer_think_text_failure_or_no_question_mark_keeps_it_done():
    assert await reply_needs_answer(_Gateway("no"), None, OFFERS) is False
    assert await reply_needs_answer(_Gateway("<think>yes maybe</think>No"), None, OFFERS) is False
    assert await reply_needs_answer(_Gateway(fail=True), None, ASKS) is False
    gw = _Gateway("yes")
    assert await reply_needs_answer(gw, None, "Saved the note.") is False and gw.requests == []
    assert await reply_needs_answer(None, None, ASKS) is False


# ------------------------------------------------------------------ the job step


@pytest.fixture
def store(tmp_path):
    return SQLiteStateStore(db_path=str(tmp_path / "card616.db"))


@pytest.fixture
def orch(store):
    return JobPhaseOrchestrator(store)


class _Kernel:
    def __init__(self, reply, gateway):
        self.reply, self.gateway = reply, gateway

    def _resolve_model(self, profile):
        return "vllm/nemotron-3.5-lightning"

    async def stream_turn(self, profile, session_id, user_content, **kw):
        yield KernelEvent(event_type=KernelEventType.TURN_END, content=self.reply, is_finished=True)


async def _run(store, orch, sid, kernel):
    job = orch.create_job_with_phases(goal="tomato note", session_id=sid, agent_id="assistant",
                                      phase_specs=[{"name": "Execute", "success_rule": "note"}])
    phase = orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    queue: asyncio.Queue = asyncio.Queue()
    out = await chat_mod._stream_turn_bound(
        queue=queue, kernel=kernel, orch=orch, store=store, reflexion_engine=None, profile=MagicMock(id="assistant"),
        session_id=f"{sid}::phase::{phase.id}", user_content="go", approval_mode="ask", resume=False,
        job=job, phase=phase, self_verify=False,
    )
    return out, job, phase


@pytest.mark.asyncio
async def test_a_plain_question_the_model_confirms_waits_for_the_answer(store, orch):
    gw = _Gateway("yes")
    out, job, phase = await _run(store, orch, "s616_q", _Kernel(ASKS, gw))
    assert out == "question"
    assert store.get_phase(phase.id).status == PhaseStatus.QUEUED
    fresh = store.get_job(job.id)
    assert fresh.status == JobStatus.RUNNING and job_waiting_for_answer(store, fresh) is True
    assert gw.requests[0].model == "vllm/nemotron-3.5-lightning"


@pytest.mark.asyncio
async def test_a_closing_courtesy_question_is_still_done(store, orch):
    out, _, phase = await _run(store, orch, "s616_no", _Kernel(OFFERS, _Gateway("no")))
    assert out == "done" and store.get_phase(phase.id).status == PhaseStatus.DONE


@pytest.mark.asyncio
async def test_a_reply_without_a_question_never_calls_the_model(store, orch):
    gw = _Gateway("yes")
    out, _, _ = await _run(store, orch, "s616_plain", _Kernel("Saved the note to 00_Inbox/tomatoes.md.", gw))
    assert out == "done" and gw.requests == []


# ------------------------------------------------------------------ a later step asks after the answer


class _SeqKernel:
    """Saves each reply in the step's session (like the real kernel) and returns them in order."""

    def __init__(self, store, replies, gateway):
        self.store, self.replies, self.gateway, self.calls = store, list(replies), gateway, []

    def _resolve_model(self, profile):
        return "vllm/nemotron-3.5-lightning"

    async def stream_turn(self, profile, session_id, user_content, **kw):
        self.calls.append(session_id)
        reply = self.replies.pop(0)
        self.store.save_message(session_id=session_id, agent_id="assistant",
                                message=ChatMessage(role=Role.ASSISTANT, content=reply))
        yield KernelEvent(event_type=KernelEventType.TURN_END, content=reply, is_finished=True)


@pytest.mark.asyncio
async def test_a_question_from_the_next_step_reaches_the_chat_and_waits(store, orch):
    import httpx
    from fastapi import FastAPI

    from src.domain.kernel.models import AgentProfile

    sid = "s616_next"
    store.create_session(agent_id="assistant", title="t", session_id=sid)
    job = orch.create_job_with_phases(goal="garden note", session_id=sid, agent_id="assistant",
                                      phase_specs=[{"name": "Formulate", "success_rule": "plan"},
                                                   {"name": "Execute", "success_rule": "note"}])
    first = orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    store.create_session(agent_id="assistant", title="Formulate", session_id=f"{sid}::phase::{first.id}")
    orch.wait_for_answer(first.id)
    kernel = _SeqKernel(store, ["Plan: tomatoes, peppers and garlic.", ASKS], _Gateway("yes"))
    app = FastAPI()
    app.include_router(chat_mod.router)
    registry = MagicMock()
    registry.get_profile.return_value = AgentProfile(id="assistant", name="A", description="d", system_prompt="", max_turns=5)
    app.state.registry, app.state.kernel, app.state.job_orchestrator = registry, kernel, orch
    app.state.reflexion_engine, app.state.store, app.state.telemetry = None, store, MagicMock()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        body = (await c.post("/api/chat/stream", json={"agent_id": "assistant", "session_id": sid,
                                                       "content": "Tomatoes, peppers and garlic"})).text
    assert len(kernel.calls) == 2  # the answered step, then the next step
    shown = [m.content for m in store.get_messages(sid) if m.role == Role.ASSISTANT]
    assert "Plan: tomatoes, peppers and garlic." in shown and ASKS in shown
    assert "waiting_answer" in body
    assert job_waiting_for_answer(store, store.get_job(job.id)) is True
