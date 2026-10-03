"""CARD-608: job step chats are not listed in Recent Chats. CARD-609: a step a restart cut off is resumable.

CARD-609 is the CARD-491 regression: Stop no longer re-queues a RUNNING phase with no chat worker, and the
CARD-530 startup repair only fails queued/DONE phases, so a restart mid-step left the chat busy for good.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.kill_resume import SERVER_RESTART_REASON, job_stopped_by_operator
from src.application.orchestration.session_activity import is_job_step_session, job_has_running_phase
from src.application.orchestration.stuck_phase_reconciler import reconcile_stuck_phases, requeue_interrupted_phases
from src.domain.orchestration.models import JobStatus, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import chat as chat_mod
from tests.unit.orchestration.test_card259_kill_resume import _two_phase_job

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def store(tmp_path):
    return SQLiteStateStore(db_path=str(tmp_path / "card608.db"))


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


# ---------------------------------------------------------------- CARD-609
@pytest.mark.asyncio
async def test_609_restart_requeues_a_running_step_so_the_chat_shows_resume(store, orch):
    sid = "sess_609_restart"
    job = _two_phase_job(orch, session_id=sid)
    phase = store.list_phases_for_job(job.id)[0]
    orch.start_phase(phase.id)  # the server dies here: RUNNING with no worker
    assert job_has_running_phase(store, store.get_job(job.id)) is True

    assert requeue_interrupted_phases(store) == [job.id]

    assert store.get_phase(phase.id).status == PhaseStatus.QUEUED
    assert store.get_job(job.id).status == JobStatus.RUNNING  # still open, same job id
    assert store.get_latest_job_phase_checkpoint(job.id).last_fail_reason == SERVER_RESTART_REASON
    assert job_stopped_by_operator(store, store.get_job(job.id)) is True
    assert job_has_running_phase(store, store.get_job(job.id)) is False
    async with _client(store, orch) as c:
        status = (await c.get(f"/api/sessions/{sid}/status")).json()
        journey = (await c.get(f"/api/chat/sessions/{sid}/journey")).json()
        activity = (await c.get("/api/sessions/activity")).json()
    assert status["is_running"] is False  # Send is shown again
    assert journey["jobs"][0]["stopped"] is True  # the strip offers Resume
    assert sid not in activity["running"]  # Recent Chats does not say Replying

    # Resume continues the same job from the checkpoint.
    resumed = orch.resume_after_crash(job.id)
    assert resumed.ok and resumed.resumed_from_checkpoint
    assert requeue_interrupted_phases(store) == []  # idempotent: nothing running now


def test_609_leaves_parked_finished_and_never_started_work_alone(store, orch):
    parked = _two_phase_job(orch, session_id="sess_609_parked")
    p = store.list_phases_for_job(parked.id)[0]
    orch.start_phase(p.id)
    p = store.get_phase(p.id)
    p.status = PhaseStatus.WAITING_APPROVAL
    store.update_phase(p)
    fresh = _two_phase_job(orch, session_id="sess_609_fresh")  # queued, never ran

    assert requeue_interrupted_phases(store) == []
    assert store.get_phase(p.id).status == PhaseStatus.WAITING_APPROVAL
    assert job_stopped_by_operator(store, store.get_job(fresh.id)) is False


def test_609_card530_repair_still_leaves_a_restart_requeued_job_resumable(store, orch):
    job = _two_phase_job(orch, session_id="sess_609_530")
    orch.start_phase(store.list_phases_for_job(job.id)[0].id)
    requeue_interrupted_phases(store)
    assert reconcile_stuck_phases(store) == []
    assert store.get_job(job.id).status == JobStatus.RUNNING


def test_609_startup_runs_the_repair_after_the_card530_one():
    src = (ROOT / "src/web/app.py").read_text(encoding="utf-8")
    assert "requeue_interrupted_phases(store)" in src
    assert src.index("reconcile_stuck_phases(store)") < src.index("requeue_interrupted_phases(store)")


# ---------------------------------------------------------------- CARD-608
@pytest.mark.asyncio
async def test_608_recent_chats_hides_job_steps_but_keeps_their_approval_on_the_parent(store, orch):
    chat = store.create_session(agent_id="autoreiv", title="Plan a trip")
    step = store.create_session(agent_id="autoreiv", title="Execute", session_id=f"{chat.id}::phase::phase_x")
    child = store.create_session(agent_id="developer", title="Hand-off", session_id=f"{chat.id}_child_dev1")
    store.create_approval(session_id=step.id, agent_id="autoreiv", tool_name="wiki_note_create", arguments={})
    async with _client(store, orch) as c:
        rows = (await c.get("/api/sessions")).json()
        everything = (await c.get("/api/sessions?include_steps=true")).json()
        activity = (await c.get("/api/sessions/activity")).json()
    ids = [r["id"] for r in rows]
    assert step.id not in ids and not any("::phase::" in i for i in ids)
    assert chat.id in ids and child.id in ids  # a hand-off chat is another agent's chat; it stays
    assert next(r for r in rows if r["id"] == chat.id)["waiting_approval"] is True  # signal kept on the parent
    assert activity["waiting_approval"] == [chat.id]
    assert step.id in [r["id"] for r in everything]  # scripts can still list steps


def test_608_deleting_a_chat_removes_its_hidden_step_sessions_only(store):
    chat = store.create_session(agent_id="autoreiv", title="A")
    other = store.create_session(agent_id="autoreiv", title="B")
    store.create_session(agent_id="autoreiv", title="Formulate", session_id=f"{chat.id}::phase::p1")
    keep = store.create_session(agent_id="autoreiv", title="Formulate", session_id=f"{other.id}::phase::p1")
    assert store.delete_session(chat.id) is True
    left = {s.id for s in store.list_sessions()}
    assert left == {other.id, keep.id}
    assert store.delete_session("missing") is False


def test_608_step_session_marker():
    assert is_job_step_session("abc::phase::phase_1") is True
    assert is_job_step_session("abc_child_dev") is False
    assert is_job_step_session("abc") is False
