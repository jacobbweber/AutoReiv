"""
MultiProviderGateway Application Service [REQ-GW-002, REQ-GW-005].
Orchestrates multi-provider routing, fallback chains, and stream demuxing.
"""

import asyncio
import logging
import random
from typing import AsyncIterator, Dict, List, Optional, Tuple

from src.application.gateway.demuxer import ReasoningDemuxer
from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.errors import (
    AllProvidersFailedError,
    AuthenticationError,
    GatewayError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from src.domain.gateway.models import (
    CompletionRequest,
    CompletionResponse,
    StreamChunk,
)
from src.domain.settings.models import ModelDescriptor

logger = logging.getLogger(__name__)


class MultiProviderGateway:
    """
    Central router and fallback orchestrator for LLM backends.
    """

    def __init__(self, default_provider_id: Optional[str] = None):
        self._providers: Dict[str, LLMProviderPort] = {}
        self.default_provider_id = default_provider_id
        self.default_model_id: Optional[str] = None

    def register_provider(self, provider: LLMProviderPort) -> None:
        """Register a provider adapter instance."""
        self._providers[provider.provider_id] = provider
        if self.default_provider_id is None:
            self.default_provider_id = provider.provider_id

    def get_provider(self, provider_id: str) -> Optional[LLMProviderPort]:
        """Lookup provider adapter by ID."""
        return self._providers.get(provider_id)

    def resolve_provider(self, model_identifier: str) -> Tuple[LLMProviderPort, str]:
        """
        Parse provider ID and model name from identifier.
        e.g. 'ollama/qwen2.5:7b' -> (OllamaAdapter, 'qwen2.5:7b')
        e.g. 'gpt-4o-mini' -> (OpenAIAdapter, 'gpt-4o-mini')
        """
        if "/" in model_identifier:
            provider_id, model_name = model_identifier.split("/", 1)
            provider = self._providers.get(provider_id)
            if provider is not None:
                return provider, model_name

        if self.default_provider_id and self.default_provider_id in self._providers:
            return self._providers[self.default_provider_id], model_identifier

        raise ModelNotFoundError(model_identifier, "No provider registered to handle this model.")

    @staticmethod
    def calculate_backoff(
        attempt: int,
        initial_delay: float = 0.2,
        backoff_factor: float = 2.0,
        max_delay: float = 4.0,
    ) -> float:
        """
        Calculate full-jitter exponential backoff for transient retry attempts [REQ-RESIL-001].
        """
        ceiling = min(max_delay, initial_delay * (backoff_factor**attempt))
        return random.uniform(0.01, max(0.02, ceiling))

    async def _execute_with_retry(
        self,
        provider: LLMProviderPort,
        candidate_req: CompletionRequest,
        max_retries: int = 2,
        initial_delay: float = 0.2,
        backoff_factor: float = 2.0,
        max_delay: float = 4.0,
    ) -> CompletionResponse:
        """Execute candidate request with localized exponential backoff and jitter for transient errors."""
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                return await provider.complete(candidate_req)
            except AuthenticationError:
                raise
            except (ProviderUnavailableError, GatewayError) as e:
                last_err = e
                if attempt < max_retries:
                    backoff = self.calculate_backoff(
                        attempt=attempt,
                        initial_delay=initial_delay,
                        backoff_factor=backoff_factor,
                        max_delay=max_delay,
                    )
                    logger.warning(
                        f"Transient error on {candidate_req.model} (attempt {attempt + 1}/{max_retries + 1}). Retrying in {backoff:.2f}s..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise
            except Exception:
                raise
        if last_err:
            raise last_err
        raise GatewayError("Execution failed without specific error", provider_id=provider.provider_id)

    async def complete(
        self,
        request: CompletionRequest,
        fallback_models: Optional[List[str]] = None,
        max_retries: int = 1,
    ) -> CompletionResponse:
        """
        Execute completion with automatic fallback on connection or server failures.
        """
        candidates = [request.model] + (fallback_models or [])
        failures: Dict[str, str] = {}

        for model_candidate in candidates:
            try:
                provider, _ = self.resolve_provider(model_candidate)
                candidate_req = request.model_copy(update={"model": model_candidate})
                return await self._execute_with_retry(provider, candidate_req, max_retries=max_retries)

            except AuthenticationError:
                # Auth errors are non-retryable credential mistakes, fail fast
                raise
            except (ProviderUnavailableError, ModelNotFoundError, GatewayError, Exception) as e:
                provider_id = getattr(e, "provider_id", "unknown")
                if provider_id == "unknown" and "/" in model_candidate:
                    provider_id = model_candidate.split("/")[0]
                failures[provider_id] = str(e)
                logger.warning(
                    f"Execution failed on candidate '{model_candidate}' ({provider_id}): {e}. Attempting fallback..."
                )

        raise AllProvidersFailedError(
            f"All {len(candidates)} candidate providers failed execution.",
            failures=failures,
        )

    async def stream(
        self,
        request: CompletionRequest,
        fallback_models: Optional[List[str]] = None,
        demux_reasoning: bool = True,
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming with candidate fallback on immediate connection failures
        and optional reasoning token demuxing.
        """
        candidates = [request.model] + (fallback_models or [])
        failures: Dict[str, str] = {}
        active_stream = None

        for model_candidate in candidates:
            try:
                provider, _ = self.resolve_provider(model_candidate)
                candidate_req = request.model_copy(update={"model": model_candidate, "stream": True})
                raw_gen = provider.stream(candidate_req)
                # Test the generator by pulling the first item or catching immediate errors
                active_stream = raw_gen
                break
            except AuthenticationError:
                raise
            except (ProviderUnavailableError, ModelNotFoundError, GatewayError, Exception) as e:
                provider_id = getattr(e, "provider_id", "unknown")
                if provider_id == "unknown" and "/" in model_candidate:
                    provider_id = model_candidate.split("/")[0]
                failures[provider_id] = str(e)
                continue

        if active_stream is None:
            raise AllProvidersFailedError(
                f"All {len(candidates)} candidate providers failed to initialize stream.",
                failures=failures,
            )

        if demux_reasoning:
            demuxer = ReasoningDemuxer()
            async for chunk in demuxer.demux_stream(active_stream):
                yield chunk
        else:
            async for chunk in active_stream:
                yield chunk

    async def list_models(self, provider_id: Optional[str] = None) -> List[ModelDescriptor]:
        """
        Query available models across all registered providers or a specific provider.
        """
        if provider_id:
            provider = self._providers.get(provider_id)
            if not provider:
                return []
            return await provider.list_models()

        all_models: List[ModelDescriptor] = []
        for provider in self._providers.values():
            try:
                models = await provider.list_models()
                all_models.extend(models)
            except Exception as e:
                logger.warning(f"Failed to list models from provider '{provider.provider_id}': {e}")
        return all_models
