"""CARD-475: images go out only for the current turn and only to vision models.

[REQ-475-001] text-only model: no image bytes, a note to the model, a notice to the user.
[REQ-475-002] only the latest user message carries images; earlier ones never re-send.
[REQ-475-005] a 'not a multimodal model' rejection retries once without images.
"""

from __future__ import annotations

import base64
from typing import AsyncIterator, List

import pytest

from src.application.gateway.attachment_images import image_notice_text
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.gateway.model_capabilities import OVERRIDES_SETTING, ModelCapabilityResolver
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.errors import GatewayError
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
)
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

D6 = (
    "This model can't view images, so it only saw the file name `shot.png`. "
    "Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures."
)


def _image(tmp_path, name: str = "shot.png"):
    p = tmp_path / f"abc123_{name}"
    p.write_bytes(PNG)
    return p


def _image_turn(path, name: str = "shot.png", text: str = "what is this?") -> str:
    # Same shape chat.format_prompt_with_attachments writes [CARD-143].
    return (
        f"{text}\n\n---\n![{name}](/api/chat/attachments/abc123/{name})\n"
        f"*(Attached Image: `{name}`, {len(PNG)} bytes, format: `image/png`, Local Path: `{path}`)*"
    )


class RecordingProvider(LLMProviderPort):
    provider_id = "vllm"

    def __init__(self, reject_images_times: int = 0):
        self.requests: List[CompletionRequest] = []
        self.reject_images_times = reject_images_times

    def _maybe_reject(self, request: CompletionRequest) -> None:
        if self.reject_images_times and any(m.images for m in request.messages):
            self.reject_images_times -= 1
            raise GatewayError("nemotron-3.5-lightning is not a multimodal model", provider_id="vllm")

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        self._maybe_reject(request)
        return CompletionResponse(model=request.model, message=ChatMessage(role=Role.ASSISTANT, content="ok"))

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        self._maybe_reject(request)
        yield StreamChunk(content="ok", is_finished=True, finish_reason="stop")

    async def list_models(self):
        return []


def _gateway(provider, settings=None) -> MultiProviderGateway:
    gw = MultiProviderGateway()
    gw.register_provider(provider)
    settings = settings or {}
    gw.set_capability_resolver(
        ModelCapabilityResolver(settings_getter=lambda key, default=None: settings.get(key, default))
    )
    return gw


async def _drain(gen) -> List[StreamChunk]:
    return [c async for c in gen]


def test_notice_wording_is_exactly_d6():
    assert image_notice_text(["shot.png"]) == D6


@pytest.mark.asyncio
async def test_text_only_model_gets_no_image_bytes_but_a_note_and_a_notice(tmp_path):
    provider = RecordingProvider()
    gw = _gateway(provider)
    req = CompletionRequest(
        model="vllm/nemotron-3.5-lightning",
        messages=[ChatMessage(role=Role.USER, content=_image_turn(_image(tmp_path)))],
    )
    chunks = await _drain(gw.stream(req))

    sent = provider.requests[0].messages[-1]
    assert not sent.images
    assert "cannot view images" in sent.content
    notices = [c.notice for c in chunks if c.notice]
    assert len(notices) == 1
    assert notices[0]["message"] == D6
    assert notices[0]["files"] == ["shot.png"]
    assert any(c.content == "ok" for c in chunks)


@pytest.mark.asyncio
async def test_vision_model_gets_the_current_turn_image(tmp_path):
    provider = RecordingProvider()
    gw = _gateway(provider, {OVERRIDES_SETTING: {"vllm/gemma-4-26b-a4b": True}})
    path = _image(tmp_path)
    req = CompletionRequest(
        model="vllm/gemma-4-26b-a4b",
        messages=[ChatMessage(role=Role.USER, content=_image_turn(path))],
    )
    chunks = await _drain(gw.stream(req))

    sent = provider.requests[0].messages[-1]
    assert sent.images and len(sent.images) == 1
    assert sent.images[0]["path"] == str(path)
    assert not any(c.notice for c in chunks)


@pytest.mark.asyncio
async def test_earlier_images_are_never_resent_even_to_vision_models(tmp_path):
    provider = RecordingProvider()
    gw = _gateway(provider, {OVERRIDES_SETTING: {"vllm/gemma-4-26b-a4b": True}})
    old = _image(tmp_path, "old.png")
    req = CompletionRequest(
        model="vllm/gemma-4-26b-a4b",
        messages=[
            ChatMessage(role=Role.USER, content=_image_turn(old, "old.png")),
            ChatMessage(role=Role.ASSISTANT, content="A cat."),
            ChatMessage(role=Role.USER, content="Hi"),
        ],
    )
    chunks = await _drain(gw.stream(req))
    assert all(not m.images for m in provider.requests[0].messages)
    assert not any(c.notice for c in chunks)


@pytest.mark.asyncio
async def test_poisoned_text_only_session_next_hi_sends_no_images(tmp_path):
    provider = RecordingProvider()
    gw = _gateway(provider)
    old = _image(tmp_path, "old.png")
    req = CompletionRequest(
        model="vllm/nemotron-3.5-lightning",
        messages=[
            ChatMessage(role=Role.USER, content=_image_turn(old, "old.png")),
            ChatMessage(role=Role.USER, content="Hi"),
        ],
    )
    chunks = await _drain(gw.stream(req))
    assert all(not m.images for m in provider.requests[0].messages)
    assert not any(c.notice for c in chunks)
    assert provider.requests[0].messages[-1].content == "Hi"


@pytest.mark.asyncio
async def test_not_multimodal_rejection_retries_once_without_images(tmp_path):
    provider = RecordingProvider(reject_images_times=1)
    resolver_settings = {OVERRIDES_SETTING: {}}
    gw = _gateway(provider, resolver_settings)
    # Name guess says vision; the provider disagrees.
    req = CompletionRequest(
        model="vllm/fake-vision-model",
        messages=[ChatMessage(role=Role.USER, content=_image_turn(_image(tmp_path)))],
    )
    chunks = await _drain(gw.stream(req))

    assert len(provider.requests) == 2
    assert provider.requests[0].messages[-1].images
    assert not provider.requests[1].messages[-1].images
    assert [c.notice["message"] for c in chunks if c.notice] == [D6]
    assert any(c.content == "ok" for c in chunks)
    assert gw.capability_resolver.can_view_images("vllm/fake-vision-model") is False


@pytest.mark.asyncio
async def test_complete_path_gates_images_too(tmp_path):
    provider = RecordingProvider()
    gw = _gateway(provider)
    req = CompletionRequest(
        model="vllm/nemotron-3.5-lightning",
        messages=[ChatMessage(role=Role.USER, content=_image_turn(_image(tmp_path)))],
    )
    resp = await gw.complete(req)
    assert resp.message.content == "ok"
    sent = provider.requests[0].messages[-1]
    assert not sent.images
    assert "cannot view images" in sent.content


def test_openai_adapter_does_not_scan_history_for_local_paths(tmp_path):
    adapter = OpenAIProviderAdapter(base_url="http://spark.test/v1", provider_id="vllm", api_key="")
    formatted = adapter._format_messages([ChatMessage(role=Role.USER, content=_image_turn(_image(tmp_path)))])
    assert isinstance(formatted[0]["content"], str)


def test_ollama_adapter_does_not_scan_history_for_local_paths(tmp_path):
    adapter = OllamaProviderAdapter(base_url="http://localhost:11434")
    formatted = adapter._format_messages([ChatMessage(role=Role.USER, content=_image_turn(_image(tmp_path)))])
    assert "images" not in formatted[0]


def test_adapters_send_images_set_by_the_gateway(tmp_path):
    path = _image(tmp_path)
    msg = ChatMessage(
        role=Role.USER,
        content="what is this?",
        images=[{"path": str(path), "media_type": "image/png", "filename": "shot.png"}],
    )
    oa = OpenAIProviderAdapter(base_url="http://spark.test/v1", provider_id="vllm", api_key="")
    parts = oa._format_messages([msg])[0]["content"]
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")
    ol = OllamaProviderAdapter(base_url="http://localhost:11434")
    assert len(ol._format_messages([msg])[0]["images"]) == 1
