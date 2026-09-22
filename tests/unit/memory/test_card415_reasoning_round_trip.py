"""CARD-415: assistant reasoning persists through SQLite and GET messages shape."""

import os
import tempfile

import pytest

from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass


@pytest.fixture
def store(temp_db_path):
    s = SQLiteStateStore(db_path=temp_db_path)
    s.initialize_db()
    return s


def test_assistant_reasoning_round_trip(store):
    session = store.create_session(agent_id="general-assistant", title="CARD-415")
    store.save_message(
        session_id=session.id,
        agent_id="general-assistant",
        message=ChatMessage(role=Role.USER, content="Why?"),
    )
    store.save_message(
        session_id=session.id,
        agent_id="general-assistant",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="Because.",
            reasoning="Step 1: consider options.\nStep 2: pick Because.",
        ),
    )

    history = store.get_messages(session_id=session.id)
    assert len(history) == 2
    assert history[1].role == Role.ASSISTANT
    assert history[1].content == "Because."
    assert history[1].reasoning == "Step 1: consider options.\nStep 2: pick Because."

    fetched = store.get_message(history[1].id)
    assert fetched is not None
    assert fetched.reasoning == history[1].reasoning


def test_assistant_without_reasoning_stays_none(store):
    session = store.create_session(agent_id="general-assistant", title="No CoT")
    store.save_message(
        session_id=session.id,
        agent_id="general-assistant",
        message=ChatMessage(role=Role.ASSISTANT, content="Plain reply"),
    )
    history = store.get_messages(session_id=session.id)
    assert history[0].reasoning is None


def test_replace_session_messages_preserves_reasoning(store):
    session = store.create_session(agent_id="general-assistant", title="Replace")
    store.replace_session_messages(
        session_id=session.id,
        agent_id="general-assistant",
        messages=[
            ChatMessage(role=Role.USER, content="Hi"),
            ChatMessage(role=Role.ASSISTANT, content="Yo", reasoning="think"),
        ],
    )
    history = store.get_messages(session_id=session.id)
    assert history[1].reasoning == "think"
