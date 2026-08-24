"""
Unit tests for Model Discovery & Hardware Fit [REQ-SET-002, REQ-SET-004].
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.settings.models import FitStatus, ModelDescriptor
from src.web.app import create_app


@pytest.fixture
def mock_app_with_models():
    app = create_app()
    # Mock gateway.list_models
    app.state.gateway = MagicMock()
    app.state.gateway.list_models = AsyncMock(
        return_value=[
            ModelDescriptor(
                id="ollama/llama3.2:latest",
                name="llama3.2:latest",
                provider="ollama",
                param_size_b=3.2,
                quantization="Q4_K_M",
            ),
            ModelDescriptor(
                id="ollama/gemma4:12b",
                name="gemma4:12b",
                provider="ollama",
                param_size_b=12.0,
                quantization="Q4_K_M",
            ),
            ModelDescriptor(
                id="openai/gpt-4o",
                name="gpt-4o",
                provider="openai",
                param_size_b=None,
                quantization="cloud",
            ),
        ]
    )
    return app


@pytest.mark.asyncio
async def test_model_discovery_endpoint(mock_app_with_models):
    transport = ASGITransport(app=mock_app_with_models)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/models/discover?available_ram_gib=16.0")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert len(data["models"]) == 3

        llama = next(m for m in data["models"] if m["name"] == "llama3.2:latest")
        assert llama["fit_status"] in [FitStatus.OPTIMAL.value, FitStatus.RUNNABLE.value]
        assert llama["estimated_ram_gb"] > 0


@pytest.mark.asyncio
async def test_model_discovery_with_custom_host():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/models/discover?provider_id=ollama&host_url=http://127.0.0.1:11434&available_ram_gib=16.0"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
