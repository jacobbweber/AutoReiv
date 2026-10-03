"""CARD-617: once a job step's card is decided, the chat's park note says so (no stale "Approve or reject above")."""

from __future__ import annotations

from src.application.orchestration.chat_job_binding import park_note, settle_park_note
from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _store_with_park():
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    sid = store.create_session(agent_id="autoreiv", title="t").id
    store.save_message(session_id=sid, agent_id="autoreiv", message=ChatMessage(role=Role.USER, content="do it"))
    note = "Plan done.\n\n---\n\n" + park_note("job_1", "Execute")
    store.save_message(session_id=sid, agent_id="autoreiv", message=ChatMessage(role=Role.ASSISTANT, content=note))
    return store, sid


def _last(store, sid):
    return [m.content for m in store.get_messages(session_id=sid) if m.role == Role.ASSISTANT][-1]


def test_rejected_card_rewrites_the_park_note():
    store, sid = _store_with_park()
    assert settle_park_note(store, f"{sid}::phase::p1", "REJECTED")
    text = _last(store, sid)
    assert text.endswith("Job job_1 paused for approval during Execute; the card was rejected.")
    assert "Approve or reject above" not in text and text.startswith("Plan done.")


def test_approved_card_says_approved():
    store, sid = _store_with_park()
    assert settle_park_note(store, f"{sid}::phase::p1", "approved")
    assert _last(store, sid).endswith("the card was approved.")


def test_plain_chat_approvals_are_left_alone():
    store, sid = _store_with_park()
    assert not settle_park_note(store, sid, "REJECTED")  # not a job step session
    assert "Approve or reject above" in _last(store, sid)
