"""
Unit tests for Provider Presets Registry [REQ-SET-001, REQ-SET-006].
"""

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.settings.presets import PROVIDER_PRESETS, get_preset_by_id
from src.web.app import create_app


def test_provider_presets_definitions():
    assert len(PROVIDER_PRESETS) >= 7
    ids = [p["id"] for p in PROVIDER_PRESETS]
    assert "ollama" in ids
    assert "openai" in ids
    assert "anthropic" in ids
    assert "openrouter" in ids
    assert "groq" in ids
    assert "deepseek" in ids
    assert "vllm" in ids

    ollama = get_preset_by_id("ollama")
    assert ollama is not None
    assert ollama["default_url"] == "http://127.0.0.1:11434"
    assert ollama["requires_key"] is False


@pytest.mark.asyncio
async def test_get_presets_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/settings/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "presets" in data
        assert len(data["presets"]) >= 7
