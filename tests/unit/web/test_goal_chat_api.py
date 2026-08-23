"""
Integration tests for Goal Mode Chat API [REQ-PLAN-006].
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ChatMessage, Role
from src.web.app import create_app


@pytest.fixture
def mock_app():
    app = create_app()
    # Mock kernel.run_turn on app state to simulate formulation & step turns
    app.state.kernel.run_turn = AsyncMock(
        side_effect=[
            # 1. Formulation
            ChatMessage(
                role=Role.ASSISTANT,
                content='{"steps": [{"title": "Step 1: Check CPU", "description": "Run sysinfo"}]}',
            ),
            # 2. Step 1 execution
            ChatMessage(role=Role.ASSISTANT, content="Step 1 complete: CPU 15% healthy"),
            # 3. Final synthesis
            ChatMessage(role=Role.ASSISTANT, content="Goal complete: System audited successfully."),
        ]
    )
    return app


@pytest.mark.asyncio
async def test_goal_chat_api_execution(mock_app):
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/goal",
            json={
                "agent_id": "general-assistant",
                "session_id": "test_sess_goal",
                "goal": "Audit CPU and report status",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert len(data["plan"]["steps"]) == 1
        assert data["plan"]["steps"][0]["status"] == "completed"
        assert "Goal complete" in data["output"]
