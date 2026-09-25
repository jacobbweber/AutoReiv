"""
Unit tests for Multimodal Vision Gateway [CARD-144].
[REQ-VISION-001] [REQ-VISION-002] [REQ-VISION-003]
"""


from src.domain.gateway.models import ChatMessage, Role
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter
from src.infrastructure.gateway.openai_adapter import OpenAIProviderAdapter


def test_openai_adapter_formats_multimodal_images():
    adapter = OpenAIProviderAdapter(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        provider_id="gemini",
        api_key="test-key",
    )

    image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    messages = [
        ChatMessage(
            role=Role.USER,
            content="What is shown in this image?",
            images=[
                {
                    "media_type": "image/png",
                    "data_base64": image_b64,
                    "filename": "dot.png",
                }
            ],
        )
    ]

    formatted = adapter._format_messages(messages)
    assert len(formatted) == 1
    msg = formatted[0]
    assert msg["role"] == "user"
    assert isinstance(msg["content"], list)
    assert len(msg["content"]) == 2
    assert msg["content"][0] == {"type": "text", "text": "What is shown in this image?"}
    assert msg["content"][1]["type"] == "image_url"
    assert msg["content"][1]["image_url"]["url"] == f"data:image/png;base64,{image_b64}"


def test_ollama_adapter_formats_multimodal_images():
    adapter = OllamaProviderAdapter(
        base_url="http://localhost:11434",
    )

    image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    messages = [
        ChatMessage(
            role=Role.USER,
            content="Inspect diagram",
            images=[
                {
                    "media_type": "image/jpeg",
                    "data_base64": image_b64,
                    "filename": "diagram.jpg",
                }
            ],
        )
    ]

    formatted = adapter._format_messages(messages)
    assert len(formatted) == 1
    msg = formatted[0]
    assert msg["role"] == "user"
    assert msg["content"] == "Inspect diagram"
    assert "images" in msg
    assert msg["images"] == [image_b64]


def test_messages_without_images_remain_plain_string():
    adapter = OpenAIProviderAdapter(
        base_url="https://api.openai.com/v1",
        provider_id="openai",
        api_key="test-key",
    )
    messages = [
        ChatMessage(role=Role.USER, content="Just plain text without images")
    ]
    formatted = adapter._format_messages(messages)
    assert len(formatted) == 1
    assert formatted[0]["content"] == "Just plain text without images"


# CARD-475: the adapters no longer scan message text for Local Path images. The gateway
# attaches the current turn's images on ChatMessage.images, only for vision models.
# See tests/unit/gateway/test_image_turn_gating_475.py.
