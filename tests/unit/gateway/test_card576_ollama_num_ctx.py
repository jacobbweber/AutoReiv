"""CARD-576: the Ollama adapter sends num_ctx only when the request sets it (no guessed 32768 that reloads the model)."""

from src.domain.gateway.models import ChatMessage, CompletionRequest, Role
from src.infrastructure.gateway.ollama_adapter import OllamaProviderAdapter


def _req(**kw):
    return CompletionRequest(model="qwen3.8:latest", messages=[ChatMessage(role=Role.USER, content="ping")], **kw)


def test_a_request_without_num_ctx_leaves_it_to_the_server_default():
    payload = OllamaProviderAdapter()._build_payload(_req(), stream=True)
    assert "num_ctx" not in payload["options"]


def test_a_request_with_num_ctx_sends_it():
    payload = OllamaProviderAdapter()._build_payload(_req(num_ctx=262144, max_tokens=5), stream=True)
    assert payload["options"]["num_ctx"] == 262144
    assert payload["options"]["num_predict"] == 5
