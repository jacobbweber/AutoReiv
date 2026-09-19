"""Unit tests for CARD-380: Chat stream error persistence and stream failure protection [REQ-CHAT-018]."""

from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from src.domain.gateway.models import Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers.chat import ChatStreamRequest, chat_stream


@pytest.fixture
def store(tmp_path):
    s = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_worker_unhandled_exception_persists_assistant_error_message(store):
    """[REQ-CHAT-018]: When worker encounters an unhandled exception, it persists an error assistant message in SQLite."""
    session_id = "sess_error_persist_test"
    store.create_session(agent_id="autoreiv", title="Error Persistence Test", session_id=session_id)

    # Mock application state
    profile = MagicMock(id="autoreiv", model="default", max_turns=5)
    registry = MagicMock()
    registry.get_profile.return_value = profile

    kernel = MagicMock()

    # Make kernel.stream_turn raise an unhandled exception
    async def failing_stream_turn(*args, **kwargs):
        raise RuntimeError("Connection dropped to provider endpoint")
        yield  # make it a generator

    kernel.stream_turn = failing_stream_turn

    app = MagicMock()
    app.state.registry = registry
    app.state.kernel = kernel
    app.state.store = store
    app.state.job_orchestrator = None
    app.state.reflexion_engine = None

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/chat/stream",
        "headers": [],
        "app": app,
    }
    request = Request(scope)

    req = ChatStreamRequest(
        agent_id="autoreiv",
        session_id=session_id,
        content="Hello world",
        resume=False,
    )

    response = await chat_stream(request, req)
    assert response.status_code == 200

    # Consume the SSE stream to allow the background worker task to run and complete
    body_lines = []
    async for chunk in response.body_iterator:
        body_lines.append(chunk)

    all_output = "".join(body_lines)
    assert 'event: error' in all_output
    assert 'Connection dropped to provider endpoint' in all_output
    assert 'event: turn_done' in all_output

    # Assert that an assistant message was persisted into SQLite
    messages = store.get_messages(session_id)
    assistant_msgs = [m for m in messages if m.role == Role.ASSISTANT]
    assert len(assistant_msgs) >= 1
    last_assistant = assistant_msgs[-1]
    assert "⚠️ **Error**:" in last_assistant.content
    assert "Connection dropped to provider endpoint" in last_assistant.content
