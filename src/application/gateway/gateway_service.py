"""
MultiProviderGateway Application Service [REQ-GW-002, REQ-GW-005].
Orchestrates multi-provider routing, fallback chains, and stream demuxing.
"""

import asyncio
import logging
import random
from typing import AsyncIterator, Callable, Dict, List, Optional, Tuple

from src.application.gateway.attachment_images import notice_payload, prepare_image_turn
from src.application.gateway.demuxer import ReasoningDemuxer
from src.application.gateway.generation_semaphore import (
    DEFAULT_MAX_CONCURRENT_GENERATIONS,
    GenerationPools,
    GenerationSemaphore,
    provider_pool_key,
)
from src.application.gateway.model_capabilities import ModelCapabilityResolver, is_multimodal_rejection
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

    def __init__(
        self,
        default_provider_id: Optional[str] = None,
        max_concurrent_generations: int = DEFAULT_MAX_CONCURRENT_GENERATIONS,
    ):
        self._providers: Dict[str, LLMProviderPort] = {}
        self.default_provider_id = default_provider_id
        self.default_model_id: Optional[str] = None
        # CARD-585: one slot pool per provider endpoint plus one for background calls
        self._generation_pools = GenerationPools(max_concurrent_generations)
        self._capability_resolver: Optional[ModelCapabilityResolver] = None
        self._reply_cap_resolver: Optional[Callable[[], int]] = None

    def set_reply_cap_resolver(self, resolver: Callable[[], int]) -> None:
        """CARD-586: where a request without max_tokens gets its cap (Settings > Reply limits max tokens)."""
        self._reply_cap_resolver = resolver

    def _with_reply_cap(self, request: CompletionRequest, *, helper: bool) -> CompletionRequest:
        """CARD-586: every model call carries a max-token limit. Without one, vLLM generates up to the rest of the
        context window and Ollama without end. Non-streaming helper calls also get room to think (HELPER_MIN_TOKENS)."""
        from src.application.kernel.reply_limits import DEFAULT_MAX_TOKENS, HELPER_MIN_TOKENS, reply_token_limit

        cap = request.max_tokens
        if not cap:
            try:
                cap = int(self._reply_cap_resolver()) if self._reply_cap_resolver else DEFAULT_MAX_TOKENS
            except Exception:
                cap = DEFAULT_MAX_TOKENS
            cap = reply_token_limit(max(1, cap), request.num_ctx)
        elif helper and cap < HELPER_MIN_TOKENS:
            cap = max(cap, reply_token_limit(HELPER_MIN_TOKENS, request.num_ctx))
        if cap == request.max_tokens:
            return request
        return request.model_copy(update={"max_tokens": cap})

    def set_capability_resolver(self, resolver: ModelCapabilityResolver) -> None:
        """Which models can view images [CARD-475]. The app wires one backed by Settings."""
        self._capability_resolver = resolver

    @property
    def capability_resolver(self) -> ModelCapabilityResolver:
        if self._capability_resolver is None:
            self._capability_resolver = ModelCapabilityResolver()
        return self._capability_resolver

    def _prepare_images(self, request: CompletionRequest, *, force_text_only: bool = False):
        """Current-turn images only, and only for vision models [CARD-475, REQ-475-001/002]."""
        can_view = (not force_text_only) and self.capability_resolver.can_view_images(request.model)
        messages, dropped, attached = prepare_image_turn(request.messages, can_view_images=can_view)
        return request.model_copy(update={"messages": messages}), dropped, attached

    @property
    def max_concurrent_generations(self) -> int:
        return self._generation_pools.max_concurrent

    def set_max_concurrent_generations(self, value: int) -> int:
        """Resize every provider slot pool [REQ-ORCH-038, CARD-585]. Extra work queues."""
        return self._generation_pools.set_max_concurrent(value)

    @property
    def generation_pools(self) -> GenerationPools:
        return self._generation_pools

    def generation_slot_for(self, request: CompletionRequest) -> GenerationSemaphore:
        """CARD-585: background calls use the background pool; others use their provider's pool."""
        if getattr(request, "background", False):
            return self._generation_pools.background
        try:
            provider, _ = self.resolve_provider(request.model)
            key = provider_pool_key(provider)
        except Exception:
            key = "provider:unknown"
        return self._generation_pools.pool(key)

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
                if is_multimodal_rejection(e):
                    raise  # CARD-475: the caller retries once without images
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
        async with self.generation_slot_for(request):
            return await self._complete_unlocked(
                request, fallback_models=fallback_models, max_retries=max_retries
            )

    async def _complete_unlocked(
        self,
        request: CompletionRequest,
        fallback_models: Optional[List[str]] = None,
        max_retries: int = 1,
    ) -> CompletionResponse:
        request = self._with_reply_cap(request, helper=True)
        candidates = [request.model] + (fallback_models or [])
        failures: Dict[str, str] = {}

        for model_candidate in candidates:
            try:
                provider, _ = self.resolve_provider(model_candidate)
                base_req = request.model_copy(update={"model": model_candidate})
                candidate_req, _dropped, attached = self._prepare_images(base_req)
                try:
                    return await self._execute_with_retry(provider, candidate_req, max_retries=max_retries)
                except Exception as e:
                    if not (attached and is_multimodal_rejection(e)):
                        raise
                    # REQ-475-005: the provider refused images; retry once without them.
                    logger.warning("Model %s refused images (%s); retrying once without them.", model_candidate, e)
                    self.capability_resolver.mark_text_only(model_candidate)
                    retry_req, _d, _a = self._prepare_images(base_req, force_text_only=True)
                    return await self._execute_with_retry(provider, retry_req, max_retries=max_retries)

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
        async with self.generation_slot_for(request):
            inner = self._stream_unlocked(
                request, fallback_models=fallback_models, demux_reasoning=demux_reasoning
            )
            try:
                async for chunk in inner:
                    yield chunk
            finally:
                closer = getattr(inner, "aclose", None)
                if callable(closer):
                    await closer()

    async def _stream_unlocked(
        self,
        request: CompletionRequest,
        fallback_models: Optional[List[str]] = None,
        demux_reasoning: bool = True,
    ) -> AsyncIterator[StreamChunk]:
        request = self._with_reply_cap(request, helper=False)
        candidates = [request.model] + (fallback_models or [])
        failures: Dict[str, str] = {}
        active_stream = None
        provider = None
        base_req = request
        dropped: Optional[List[str]] = None
        attached = False

        for model_candidate in candidates:
            try:
                provider, _ = self.resolve_provider(model_candidate)
                base_req = request.model_copy(update={"model": model_candidate, "stream": True})
                candidate_req, dropped, attached = self._prepare_images(base_req)
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

        if dropped:
            yield StreamChunk(notice=notice_payload(dropped))

        yielded = False
        try:
            async for chunk in self._pipe(active_stream, demux_reasoning):
                yielded = True
                yield chunk
            return
        except Exception as e:
            if yielded or not attached or not is_multimodal_rejection(e):
                raise
            logger.warning("Model %s refused images (%s); retrying once without them.", base_req.model, e)
        finally:
            closer = getattr(active_stream, "aclose", None)
            if callable(closer):
                await closer()

        # REQ-475-005: the provider refused images; retry once without them, with the notice.
        self.capability_resolver.mark_text_only(base_req.model)
        retry_req, dropped, _ = self._prepare_images(base_req, force_text_only=True)
        if dropped:
            yield StreamChunk(notice=notice_payload(dropped))
        retry_stream = provider.stream(retry_req)
        try:
            async for chunk in self._pipe(retry_stream, demux_reasoning):
                yield chunk
        finally:
            closer = getattr(retry_stream, "aclose", None)
            if callable(closer):
                await closer()

    @staticmethod
    async def _pipe(stream, demux_reasoning: bool) -> AsyncIterator[StreamChunk]:
        if demux_reasoning:
            async for chunk in ReasoningDemuxer().demux_stream(stream):
                yield chunk
        else:
            async for chunk in stream:
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
