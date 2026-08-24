"""
Integration tests for Verified Chat and SRE Audit API [REQ-VERIFY-005, REQ-VERIFY-006].
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.gateway.models import ChatMessage, Role
from src.web.app import create_app


@pytest.fixture
def mock_app():
    app = create_app()
    # Mock kernel.run_turn on app state
    app.state.kernel.run_turn = AsyncMock(
        return_value=ChatMessage(
            role=Role.ASSISTANT,
            content='{"health_score": 98.0, "status": "healthy"}',
        )
    )
    return app


@pytest.mark.asyncio
async def test_verified_chat_api_success(mock_app):
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat/verified",
            json={
                "agent_id": "system-agent",
                "session_id": "test_sess_verify",
                "content": "Report health",
                "verifier_tool": "assert_json_schema",
                "verifier_args": {"required_keys": ["health_score", "status"]},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "verified"
        assert data["verification_passed"] is True
        assert "health_score" in data["output"]


@pytest.mark.asyncio
async def test_audit_agent_api(mock_app):
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/agents/audit",
            json={
                "agent_id": "auditor-critic",
                "session_id": "test_sess_audit",
                "target_content": "Plan to update database indexes",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "audited"
        assert "audit_report" in data
