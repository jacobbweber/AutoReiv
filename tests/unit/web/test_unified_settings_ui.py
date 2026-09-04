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
        # Purpose-Based Model Routing panel is removed [CARD-153 / REQ-MODEL-005]
        assert "Purpose-Based Model Routing" not in html
        assert "saveMatrixBtn" not in html
        # Assert provider preset picker exists
        assert "provPresetSelect" in html
        # Assert model picker dropdown exists
        assert "provModelSelect" in html


@pytest.mark.asyncio
async def test_provider_settings_persists_model_choice():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Save provider with a specific model choice
        save_resp = await ac.post(
            "/api/settings/providers",
            json={
                "ollama_host": "http://127.0.0.1:11434",
                "default_provider_id": "ollama",
                "default_model_id": "llama3.8",
            },
        )
        assert save_resp.status_code == 200
        data = save_resp.json()
        assert data["providers"]["default_model_id"] == "llama3.8"

        # Verify GET /api/settings returns the persisted model choice
        get_resp = await ac.get("/api/settings")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["providers"]["default_model_id"] == "llama3.8"
