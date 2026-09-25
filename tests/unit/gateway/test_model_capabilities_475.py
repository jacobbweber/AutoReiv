"""CARD-475: vision capability resolution order and provider metadata [REQ-475-003].

Order: operator override, then saved provider metadata, then the name guess,
otherwise text-only. A provider rejection learned at runtime beats metadata and
the name guess but never an explicit override.
"""

from __future__ import annotations

import httpx
import pytest

from src.application.gateway.model_capabilities import (
    METADATA_SETTING,
    OVERRIDES_SETTING,
    ModelCapabilityResolver,
)
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


def _resolver(settings: dict) -> ModelCapabilityResolver:
    return ModelCapabilityResolver(settings_getter=lambda key, default=None: settings.get(key, default))


def test_unknown_model_is_text_only():
    r = _resolver({})
    assert r.can_view_images("vllm/nemotron-3.5-lightning") is False
    assert r.vision_source("vllm/nemotron-3.5-lightning") == "default"


def test_name_guess_marks_llava_as_vision():
    r = _resolver({})
    assert r.can_view_images("ollama/llava:7b") is True
    assert r.vision_source("ollama/llava:7b") == "name"


def test_saved_provider_metadata_beats_name_and_default():
    r = _resolver({METADATA_SETTING: {"vllm/gemma-4-26b-a4b": {"vision": True}}})
    assert r.can_view_images("vllm/gemma-4-26b-a4b") is True
    assert r.vision_source("vllm/gemma-4-26b-a4b") == "provider"


def test_override_beats_metadata_and_name():
    r = _resolver(
        {
            OVERRIDES_SETTING: {"ollama/llava:7b": False, "vllm/nemotron-3.5-lightning": True},
            METADATA_SETTING: {"ollama/llava:7b": {"vision": True}},
        }
    )
    assert r.can_view_images("ollama/llava:7b") is False
    assert r.vision_source("ollama/llava:7b") == "override"
    assert r.can_view_images("vllm/nemotron-3.5-lightning") is True


def test_bare_model_name_matches_provider_prefixed_key():
    r = _resolver({METADATA_SETTING: {"vllm/gemma-4-26b-a4b": {"vision": True}}})
    assert r.can_view_images("gemma-4-26b-a4b") is True


def test_runtime_rejection_beats_metadata_but_not_override():
    r = _resolver({METADATA_SETTING: {"vllm/gemma-4-26b-a4b": {"vision": True}}})
    r.mark_text_only("vllm/gemma-4-26b-a4b")
    assert r.can_view_images("vllm/gemma-4-26b-a4b") is False
    assert r.vision_source("vllm/gemma-4-26b-a4b") == "provider_rejected"

    r2 = _resolver({OVERRIDES_SETTING: {"vllm/nemotron-3.5-lightning": True}})
    r2.mark_text_only("vllm/nemotron-3.5-lightning")
    assert r2.can_view_images("vllm/nemotron-3.5-lightning") is True


@pytest.mark.asyncio
async def test_ollama_list_models_reads_capabilities_vision():
    body = {
        "models": [
            {"name": "gemma3:4b", "details": {}, "capabilities": ["completion", "vision"]},
            {"name": "qwen3:8b", "details": {}, "capabilities": ["completion", "tools"]},
        ]
    }
    client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=body)),
    )
    adapter = OllamaProviderAdapter(base_url="http://ollama.test", client=client)
    models = {m.name: m for m in await adapter.list_models()}
    assert models["gemma3:4b"].is_multimodal is True
    assert models["qwen3:8b"].is_multimodal is False


@pytest.mark.asyncio
async def test_openai_list_models_reads_multimodal_description():
    body = {
        "data": [
            {"id": "gemma-4-26b-a4b", "description": "Gemma 4 26B multimodal (text + image)"},
            {"id": "nemotron-3.5-lightning", "description": "Fast text model"},
        ]
    }
    adapter = OpenAIProviderAdapter(base_url="http://spark.test/v1", provider_id="vllm", api_key="")
    adapter._client = httpx.AsyncClient(
        base_url="http://spark.test/v1",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=body)),
    )
    models = {m.name: m for m in await adapter.list_models()}
    assert models["gemma-4-26b-a4b"].is_multimodal is True
    assert models["nemotron-3.5-lightning"].is_multimodal is False
