"""CARD-490..494: Stop and resume, Recent Chats status, waiting-for-a-slot notice (server side).

CARD-490: the journey marks a job that Stop paused (``stopped``) so the strip offers Resume.
CARD-491: Stop cancels background tasks its turn started; with no chat worker to cancel it leaves a RUNNING phase alone.
CARD-493: GET /api/sessions and GET /api/sessions/activity say which chats are replying or need approval.
CARD-494: a stream that has to wait for a generation slot is told ``queued`` then ``dequeued``.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

import httpx
import pytest
from fastapi import FastAPI

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.generation_semaphore import SLOT_WAIT_REASON, slot_wait_listener
from src.application.gateway.ports import LLMProviderPort
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.kill_resume import job_stopped_by_operator
from src.application.orchestration.session_activity import parent_session_id, session_activity
from src.domain.gateway.models import ChatMessage, CompletionRequest, CompletionResponse, Role, StreamChunk
from src.domain.orchestration.models import PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import chat as chat_mod
from tests.unit.orchestration.test_card259_kill_resume import _two_phase_job

PREFIX = "sess_49x"


@pytest.fixture
def store(tmp_path):
    return SQLiteStateStore(db_path=str(tmp_path / "card49x.db"))


@pytest.fixture
def orch(store):
    return JobPhaseOrchestrator(store)


class _Tel:
    def record_turn_span(self, *a, **k):
        return None


def _client(store, orch) -> httpx.AsyncClient:
    app = FastAPI()
    app.include_router(chat_mod.router)
    app.state.telemetry = _Tel()
    app.state.store = store
    app.state.job_orchestrator = orch
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


@pytest.fixture(autouse=True)
def _clean_registry():
    yield
    for sid in list(chat_mod._active_stream_tasks):
        if sid.startswith(PREFIX):
            task = chat_mod._active_stream_tasks.pop(sid, None)
            if task and not task.done():
                task.cancel()
            chat_mod._active_stream_agents.pop(sid, None)


# ---------------------------------------------------------------- CARD-490
@pytest.mark.asyncio
async def test_490_journey_marks_a_job_paused_by_stop(store, orch):
    sid = f"{PREFIX}_stop"
    job = _two_phase_job(orch, session_id=sid)
    phase = store.list_phases_for_job(job.id)[0]
    orch.start_phase(phase.id)
    chat_mod._active_stream_tasks[sid] = asyncio.create_task(asyncio.sleep(30))
    async with _client(store, orch) as c:
        before = (await c.get(f"/api/chat/sessions/{sid}/journey")).json()
        ab = (await c.post(f"/api/chat/stream/{sid}/abort")).json()
        after = (await c.get(f"/api/chat/sessions/{sid}/journey")).json()
    assert before["jobs"][0]["stopped"] is False  # running is not stopped
    assert ab["checkpointed"] is True and ab["job_id"] == job.id
    assert after["jobs"][0]["stopped"] is True
    orch.start_phase(phase.id)  # Resume starts the phase again
    assert job_stopped_by_operator(store, store.get_job(job.id)) is False


def test_490_queued_job_that_was_never_stopped_is_not_stopped(store, orch):
    job = _two_phase_job(orch, session_id=f"{PREFIX}_fresh")
    assert job_stopped_by_operator(store, store.get_job(job.id)) is False


# ---------------------------------------------------------------- CARD-491
@pytest.mark.asyncio
async def test_491_abort_without_a_chat_worker_leaves_a_running_phase_alone(store, orch):
    sid = f"{PREFIX}_elsewhere"
    job = _two_phase_job(orch, session_id=sid)
    phase = store.list_phases_for_job(job.id)[0]
    orch.start_phase(phase.id)
    async with _client(store, orch) as c:
        ab = (await c.post(f"/api/chat/stream/{sid}/abort")).json()
    assert ab["task_cancelled"] is False and ab["checkpointed"] is False
    assert ab["reason"] == "not_started_by_chat" and "cannot end it" in ab["message"]
    assert store.get_phase(phase.id).status == PhaseStatus.RUNNING  # not marked QUEUED


@pytest.mark.asyncio
async def test_491_abort_with_nothing_running_says_so(store, orch):
    async with _client(store, orch) as c:
        ab = (await c.post(f"/api/chat/stream/{PREFIX}_idle/abort")).json()
    assert ab["status"] == "aborted" and ab["reason"] == "nothing_running" and ab["checkpointed"] is False


@pytest.mark.asyncio
async def test_491_stop_cancels_the_side_tasks_its_turn_started(store, orch):
    sid = f"{PREFIX}_side"
    started = asyncio.Event()
    holder = {}

    async def other_turn_side():
        await asyncio.sleep(30)

    async def worker():
        holder["mine"] = chat_mod.spawn_turn_side_task(sid, asyncio.sleep(30))
        started.set()
        await asyncio.sleep(30)

    holder["other"] = chat_mod.spawn_turn_side_task(sid, other_turn_side())  # an earlier, finished turn's task
    task = asyncio.create_task(worker())
    chat_mod._active_stream_tasks[sid] = task
    await started.wait()
    async with _client(store, orch) as c:
        ab = (await c.post(f"/api/chat/stream/{sid}/abort")).json()
    await asyncio.sleep(0)
    assert ab["task_cancelled"] is True and ab["side_tasks_cancelled"] == 1
    assert holder["mine"].cancelled() or holder["mine"].cancelling()
    assert not holder["other"].done()  # memory work of an earlier finished turn keeps going
    holder["other"].cancel()


# ---------------------------------------------------------------- CARD-493
def test_493_parent_session_id():
    assert parent_session_id("abc_child_autoreiv_1") == "abc"
    assert parent_session_id("abc::phase::p1") == "abc"
    assert parent_session_id("abc") == "abc"


@pytest.mark.asyncio
async def test_493_sessions_list_and_activity_show_replying_and_needs_approval(store, orch):
    a, b, c_, d = (f"{PREFIX}_a", f"{PREFIX}_b", f"{PREFIX}_c", f"{PREFIX}_d")
    for sid in (a, b, c_, d):
        store.create_session(agent_id="autoreiv", title=sid, session_id=sid)
    chat_mod._active_stream_tasks[a] = asyncio.create_task(asyncio.sleep(30))  # A replies in this server
    job = _two_phase_job(orch, session_id=b)  # B has a RUNNING phase
    orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    store.create_approval(session_id=f"{c_}_child_toolsmith_1", agent_id="toolsmith", tool_name="cli_exec", arguments={})
    async with _client(store, orch) as cl:
        rows = {r["id"]: r for r in (await cl.get("/api/sessions?agent_id=autoreiv")).json()}
        act = (await cl.get("/api/sessions/activity")).json()
    assert (rows[a]["is_running"], rows[a]["waiting_approval"]) == (True, False)
    assert (rows[b]["is_running"], rows[b]["waiting_approval"]) == (True, False)
    assert (rows[c_]["is_running"], rows[c_]["waiting_approval"]) == (False, True)
    assert (rows[d]["is_running"], rows[d]["waiting_approval"]) == (False, False)
    assert a in act["running"] and b in act["running"] and act["waiting_approval"] == [c_]


@pytest.mark.asyncio
async def test_493_markers_clear_when_the_work_ends(store, orch):
    sid = f"{PREFIX}_clear"
    store.create_session(agent_id="autoreiv", title="x", session_id=sid)
    task = asyncio.create_task(asyncio.sleep(30))
    chat_mod._active_stream_tasks[sid] = task
    appr = store.create_approval(session_id=sid, agent_id="autoreiv", tool_name="cli_exec", arguments={})
    assert sid in session_activity(store, chat_mod._live_stream_session_ids())["running"]
    task.cancel()
    await asyncio.sleep(0)
    store.resolve_approval(appr, "approved")
    act = session_activity(store, chat_mod._live_stream_session_ids())
    assert sid not in act["running"] and sid not in act["waiting_approval"]


# ---------------------------------------------------------------- CARD-494
class _SlowLLM(LLMProviderPort):
    provider_id = "mock"

    def __init__(self):
        self.gate = asyncio.Event()

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(model=request.model, finish_reason="stop", message=ChatMessage(role=Role.ASSISTANT, content="x"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        await self.gate.wait()
        yield StreamChunk(content="hi")
        yield StreamChunk(is_finished=True, finish_reason="stop")

    async def list_models(self):
        return []

    async def health_check(self) -> bool:
        return True


def _req():
    return CompletionRequest(model="mock/m", messages=[ChatMessage(role=Role.USER, content="hi")])


@pytest.mark.asyncio
async def test_494_a_waiting_stream_is_told_queued_then_dequeued():
    llm = _SlowLLM()
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    first_events: List = []
    second_events: List = []

    async def run(events, label):
        slot_wait_listener.set(lambda kind, data: events.append((kind, data)))
        return [c.content async for c in gw.stream(_req()) if c.content]

    t1 = asyncio.create_task(run(first_events, "a"))
    await asyncio.sleep(0.05)  # A holds the only slot
    t2 = asyncio.create_task(run(second_events, "b"))
    await asyncio.sleep(0.05)
    assert first_events == []  # A got the slot at once
    assert second_events == [("queued", {"position": 1, "reason": SLOT_WAIT_REASON})]
    llm.gate.set()
    await asyncio.gather(t1, t2)
    assert [k for k, _ in second_events] == ["queued", "dequeued"]


@pytest.mark.asyncio
async def test_494_no_listener_and_background_calls_are_quiet():
    llm = _SlowLLM()
    llm.gate.set()
    gw = MultiProviderGateway()
    gw.register_provider(llm)
    events: List = []
    slot_wait_listener.set(lambda kind, data: events.append(kind))
    async with gw.generation_slot_for(_req()):  # someone else holds the slot
        bg = asyncio.create_task(_collect(gw, _req().model_copy(update={"background": True})))
        await asyncio.sleep(0.05)
    await bg
    assert events == []  # the background pool is separate, and it never reports


async def _collect(gw, req):
    return [c async for c in gw.stream(req)]
