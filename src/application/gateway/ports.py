"""
Application Ports for LLM Providers.
"""

from typing import AsyncIterator, List, Protocol, runtime_checkable

from src.domain.gateway.models import CompletionRequest, CompletionResponse, StreamChunk
from src.domain.settings.models import ModelDescriptor


@runtime_checkable
class LLMProviderPort(Protocol):
    """Abstract port interface for an LLM backend provider."""

    provider_id: str

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a non-streaming completion request."""
        ...

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        """Execute a streaming completion request and yield incremental chunks."""
        ...

    async def list_models(self) -> List[ModelDescriptor]:
        """Fetch available models from this provider."""
        ...
