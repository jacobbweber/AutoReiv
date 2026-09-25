"""CARD-486: Stop aborts on the server; /status only says running when work is really running.

REQ-486-004: no live stream task and no RUNNING phase -> is_running False (kill-checkpointed or parked).
REQ-486-006: a server abort cancels the upstream model request (no chunks read after abort).
REQ-486-007: a parked approval stays parked on Stop.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from src.domain.orchestration.models import JobStatus, PhaseStatus
from src.web.routers import chat as chat_mod
from tests.unit.orchestration.test_card259_kill_resume import (  # noqa: F401  (fixtures)
    _two_phase_job,
    orch,
    store,
    temp_db_path,
)


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
        if sid.startswith("sess_486"):
            task = chat_mod._active_stream_tasks.pop(sid, None)
            if task and not task.done():
                task.cancel()
            chat_mod._active_stream_agents.pop(sid, None)


@pytest.mark.asyncio
async def test_req_486_004_status_not_running_after_stop_in_job_chat(store, orch):
    sid = "sess_486_job"
    job = _two_phase_job(orch, session_id=sid)
    phase = store.list_phases_for_job(job.id)[0]
    orch.start_phase(phase.id)
    chat_mod._active_stream_tasks[sid] = asyncio.create_task(asyncio.sleep(30))
    async with _client(store, orch) as c:
        assert (await c.get(f"/api/sessions/{sid}/status")).json()["is_running"] is True
        ab = (await c.post(f"/api/chat/stream/{sid}/abort")).json()
        assert ab["task_cancelled"] is True and ab["checkpointed"] is True
        assert store.get_job(job.id).status == JobStatus.RUNNING  # resumable, left open [CARD-259]
        assert store.get_phase(phase.id).status == PhaseStatus.QUEUED
        st = (await c.get(f"/api/sessions/{sid}/status")).json()
    assert st["is_running"] is False
    assert st["active_agent"] is None


@pytest.mark.asyncio
async def test_req_486_004_running_phase_without_stream_task_still_running(store, orch):
    """Work running outside this server's stream registry (phone return, CARD-154) still reads as running."""
    sid = "sess_486_phase_running"
    job = _two_phase_job(orch, session_id=sid)
    orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    async with _client(store, orch) as c:
        st = (await c.get(f"/api/sessions/{sid}/status")).json()
    assert st["is_running"] is True
    assert st["active_agent"] == "assistant"


@pytest.mark.asyncio
async def test_req_486_007_parked_approval_stays_parked_and_not_running(store, orch):
    sid = "sess_486_parked"
    job = _two_phase_job(orch, session_id=sid)
    phase = store.list_phases_for_job(job.id)[0]
    orch.start_phase(phase.id)
    orch.park_phase(phase.id)
    async with _client(store, orch) as c:
        ab = (await c.post(f"/api/chat/stream/{sid}/abort")).json()
        st = (await c.get(f"/api/sessions/{sid}/status")).json()
    assert ab["status"] == "aborted"
    assert store.get_phase(phase.id).status == PhaseStatus.WAITING_APPROVAL
    assert store.get_job(job.id).status == JobStatus.WAITING_APPROVAL
    assert st["is_running"] is False


@pytest.mark.asyncio
async def test_req_486_006_abort_cancels_the_upstream_model_stream(store, orch):
    """The adapters stream with `async with client.stream(...)`; cancelling the task must close it."""
    sid = "sess_486_upstream"
    sent = {"n": 0}

    async def slow_body():
        for i in range(200):
            sent["n"] += 1
            yield f'{{"message": {{"content": "w{i} "}}, "done": false}}\n'.encode()
            await asyncio.sleep(0.02)

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, content=slow_body())))
    seen = {"chunks": 0, "exited": False, "response": None}

    async def worker():
        try:
            async with upstream.stream("POST", "http://model/api/chat", json={"stream": True}) as resp:
                seen["response"] = resp
                async for _line in resp.aiter_lines():
                    seen["chunks"] += 1
        finally:
            seen["exited"] = True

    task = asyncio.create_task(worker())
    chat_mod._active_stream_tasks[sid] = task
    for _ in range(100):
        if seen["chunks"] >= 3:
            break
        await asyncio.sleep(0.01)
    assert seen["chunks"] >= 3
    async with _client(store, orch) as c:
        ab = (await c.post(f"/api/chat/stream/{sid}/abort")).json()
    assert ab["task_cancelled"] is True
    at_abort = seen["chunks"]
    await asyncio.sleep(0.2)
    assert task.done()
    assert seen["exited"] is True
    assert seen["response"].is_closed
    assert seen["chunks"] == at_abort  # nothing read from the model after the abort
    assert sent["n"] < 200  # the model stream did not run to the end
    await upstream.aclose()
