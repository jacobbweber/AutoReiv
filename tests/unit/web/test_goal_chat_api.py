"""
Deprecated Goal Chat API thin-wrap [CARD-215 / REQ-JOBGRAPH-001b, 002].
Formulates into Job/Phase only — no execute_plan authority.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ChatMessage, Role
from src.web.app import create_app


@pytest.fixture
def mock_app():
    app = create_app()
    app.state.kernel.gateway.complete = AsyncMock(
        return_value=MagicMock(
            message=ChatMessage(
                role=Role.ASSISTANT,
                content='{"steps": [{"title": "Step 1: Check CPU", "description": "Run sysinfo"}]}',
            )
        )
    )
    app.state.kernel.run_turn = AsyncMock(
        side_effect=AssertionError("deprecated /api/chat/goal must not execute_plan/run_turn")
    )
    return app


@pytest.mark.asyncio
async def test_goal_chat_api_formulates_only(mock_app):
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
        assert data["status"] == "formulated"
        assert data["deprecated"] is True
        assert data.get("output") in (None, "")
        assert len(data["plan"]["steps"]) == 1
        assert data.get("job_id")
        job = mock_app.state.store.get_job(data["job_id"])
        phases = mock_app.state.store.list_phases_for_job(job.id)
        assert len(phases) >= 1
        assert all(p.status.value in {"queued", "waiting_approval"} for p in phases)
