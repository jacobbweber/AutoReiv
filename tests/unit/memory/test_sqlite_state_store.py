"""
Unit tests for SQLite WAL State Store & Session Checkpointer [REQ-KERNEL-004].
"""

import os
import tempfile

import pytest

from src.domain.gateway.models import ChatMessage, Role, ToolCall
from src.domain.telemetry.models import TelemetrySpan
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


def test_sqlite_wal_initialization(store):
    journal_mode = store.get_journal_mode()
    assert journal_mode.lower() == "wal"


def test_session_lifecycle(store):
    session = store.create_session(agent_id="general-assistant", title="Morning Plan")
    assert session.id is not None
    assert session.agent_id == "general-assistant"
    assert session.title == "Morning Plan"

    fetched = store.get_session(session.id)
    assert fetched is not None
    assert fetched.id == session.id

    sessions = store.list_sessions(agent_id="general-assistant")
    assert len(sessions) == 1

    deleted = store.delete_session(session.id)
    assert deleted is True
    assert store.get_session(session.id) is None


def test_message_persistence_and_ordering(store):
    session = store.create_session(agent_id="general-assistant", title="Test Chat")

    msg1 = ChatMessage(role=Role.USER, content="Hello AutoReiv")
    msg2 = ChatMessage(
        role=Role.ASSISTANT,
        content="I will check your tasks.",
        tool_calls=[ToolCall(id="c1", name="task_list", arguments={"status": "pending"})],
    )
    msg3 = ChatMessage(role=Role.TOOL, content='{"tasks": []}', tool_call_id="c1", name="task_list")
    msg4 = ChatMessage(role=Role.ASSISTANT, content="You have no pending tasks.")

    store.save_message(session_id=session.id, agent_id="general-assistant", message=msg1)
    store.save_message(session_id=session.id, agent_id="general-assistant", message=msg2)
    store.save_message(session_id=session.id, agent_id="general-assistant", message=msg3)
    store.save_message(session_id=session.id, agent_id="general-assistant", message=msg4)

    history = store.get_messages(session_id=session.id)
    assert len(history) == 4
    assert history[0].role == Role.USER
    assert history[0].content == "Hello AutoReiv"
    assert history[1].tool_calls is not None
    assert history[1].tool_calls[0].name == "task_list"
    assert history[2].role == Role.TOOL
    assert history[2].tool_call_id == "c1"
    assert history[3].content == "You have no pending tasks."


def test_telemetry_span_persistence(store):
    span = TelemetrySpan(
        id="span_101",
        session_id="sess_abc",
        agent_id="linux-sysadmin",
        span_type="tool",
        name="cli_exec",
        duration_ms=120.5,
        prompt_tokens=0,
        completion_tokens=0,
        success=True,
        metadata={"cmd": "uptime"},
    )
    store.save_telemetry_span(span)

    spans = store.get_telemetry_spans(agent_id="linux-sysadmin")
    assert len(spans) == 1
    assert spans[0].name == "cli_exec"
    assert spans[0].duration_ms == 120.5
    assert spans[0].metadata["cmd"] == "uptime"
