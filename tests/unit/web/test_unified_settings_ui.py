"""
Unit tests for Settings Studio UI integration [REQ-SET-003, REQ-SET-005].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.web.app import create_app


@pytest.mark.asyncio
async def test_settings_studio_page_renders_clean_matrix():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
        assert resp.status_code == 200
        html = resp.text
        # Assert no Hermes jargon exists in user-facing HTML
        assert "Hermes" not in html
        assert "Purpose-Based Model Routing" in html or "Purpose-Based" in html
        # Assert provider preset picker exists
        assert "provPresetSelect" in html
        # Assert model picker dropdown exists
        assert "provModelSelect" in html
