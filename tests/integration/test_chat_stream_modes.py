"""
Integration tests for Visual Goal Mode & Reflexion Streaming [REQ-CHAT-010 - REQ-CHAT-014].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.app import create_app


@pytest.fixture
def stream_app():
    store = SQLiteStateStore(db_path=":memory:")
    app = create_app(state_store=store)
    app.state.store.create_session(session_id="test_sess_stream_goal", agent_id="assistant", title="Goal Test")
    app.state.store.create_session(session_id="test_sess_stream_verify", agent_id="assistant", title="Verify Test")
    # Mock kernel.run_turn for plan formulation and steps
    app.state.kernel.run_turn = AsyncMock(
        side_effect=[
            # 1. Formulation JSON
            ChatMessage(
                role=Role.ASSISTANT,
                content='{"steps": [{"title": "Step 1: Discover", "description": "Scan files"}, {"title": "Step 2: Synthesize", "description": "Write report"}]}',
            ),
            # 2. Step 1 execution
            ChatMessage(role=Role.ASSISTANT, content="Step 1 complete: Found 3 files."),
            # 3. Step 2 execution
            ChatMessage(role=Role.ASSISTANT, content="Step 2 complete: Report written."),
            # 4. Final synthesis
            ChatMessage(role=Role.ASSISTANT, content="All steps completed successfully."),
        ]
    )
    app.state.kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(
            message=ChatMessage(
                role=Role.ASSISTANT,
                content='{"is_valid": true, "discrepancies": []}',
            )
        )
    )
    return app


@pytest.mark.asyncio
async def test_chat_stream_goal_mode_events(stream_app):
    """Assert that goal_mode=True emits plan_formulated, step_start, and step_complete SSE events [REQ-CHAT-010, REQ-CHAT-011]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_goal",
                "content": "Scan files and generate report",
                "goal_mode": True,
                "self_verify": False,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: plan_formulated" in body
        assert "event: step_start" in body
        assert "event: step_complete" in body
        assert "event: turn_done" in body


@pytest.mark.asyncio
async def test_chat_stream_reflexion_events(stream_app):
    """Assert that self_verify=True emits reflexion_attempt and reflexion_verified SSE events [REQ-CHAT-012, REQ-CHAT-014]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_verify",
                "content": "Scan files and generate report",
                "goal_mode": False,
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: reflexion_attempt" in body
        assert "event: turn_done" in body


@pytest.mark.asyncio
async def test_chat_stream_dual_mode_events(stream_app):
    """Assert that goal_mode=True AND self_verify=True emits both plan and reflexion SSE events [REQ-CHAT-014]."""
    transport = ASGITransport(app=stream_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/stream",
            json={
                "agent_id": "assistant",
                "session_id": "test_sess_stream_goal",
                "content": "Scan files and generate report",
                "goal_mode": True,
                "self_verify": True,
            },
        )
        assert resp.status_code == 200
        body = resp.text
        assert "event: plan_formulated" in body
        assert "event: step_start" in body
        assert "event: reflexion_attempt" in body
        assert "event: reflexion_verified" in body
        assert "event: step_complete" in body
        assert "event: turn_done" in body
