"""
Negative assertion: verify that retired Goal Chat API returns 404 [CARD-395].
All standing multi-step Chat executes exclusively via /api/chat/stream.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.web.app import create_app


@pytest.fixture
def mock_app():
    return create_app()


@pytest.mark.asyncio
async def test_goal_chat_api_endpoint_excised_and_returns_404(mock_app):
    """Verify that POST /api/chat/goal is fully excised and returns 404."""
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
        assert resp.status_code == 404
