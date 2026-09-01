"""
OpenAI-Compatible Provider Adapter [REQ-GW-004].
Communicates with OpenAI-compatible endpoints (/v1/chat/completions).
Works with OpenAI, OpenRouter, Anthropic-proxies, LocalAI, vLLM, and LM Studio.
"""

import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from src.application.gateway.ports import LLMProviderPort
from src.domain.gateway.errors import (
    AuthenticationError,
    GatewayError,
    ModelNotFoundError,
    ProviderUnavailableError,
    RateLimitError,
)
from src.domain.gateway.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
    ToolDefinition,
)
from src.domain.settings.models import ModelDescriptor

logger = logging.getLogger(__name__)


class OpenAIProviderAdapter(LLMProviderPort):
    """Adapter for OpenAI and OpenAI-compatible endpoints."""

    provider_id: str = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 60.0,
        provider_id: str = "openai",
    ):
        self.provider_id = provider_id
        self.api_key = api_key or ""
        raw_url = (base_url or "https://api.openai.com/v1").strip()
        if not raw_url.startswith(("http://", "https://")):
            raw_url = f"https://{raw_url}"
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
        self._client = client

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(connect=10.0, read=self.timeout, write=10.0, pool=10.0),
                limits=self.limits,
            )
        return self._client

    def _format_model_name(self, model: str) -> str:
        """Strip provider prefix if present and handle 'default' model fallback."""
        if model.startswith(f"{self.provider_id}/"):
            model = model[len(f"{self.provider_id}/") :]
        for prefix in (
            "openai/",
            "gemini/",
            "lmstudio/",
            "vllm/",
            "anthropic/",
            "openrouter/",
            "groq/",
            "deepseek/",
            "together/",
        ):
            if model.startswith(prefix):
                model = model[len(prefix) :]
                break

        if model.startswith("models/"):
            model = model[len("models/") :]

        if model == "default" or not model:
            from src.application.settings.presets import get_preset_by_id

            preset = get_preset_by_id(self.provider_id)
            if preset and preset.get("recommended_models"):
                return preset["recommended_models"][0]
            return "gpt-4o-mini"
        return model

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        # Map tool_call_id to tool_name from assistant messages
        tool_id_to_name: Dict[str, str] = {}
        for m in messages:
            if m.tool_calls:
                for tc in m.tool_calls:
                    if tc.id and tc.name:
                        tool_id_to_name[tc.id] = tc.name

        raw_items = []
        for m in messages:
            content_val = m.content if m.content is not None else ""
            item: Dict[str, Any] = {
                "role": m.role.value,
                "content": content_val,
            }
            if m.tool_calls:
                formatted_tcs = []
                for tc in m.tool_calls:
                    tc_dict: Dict[str, Any] = {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                            if isinstance(tc.arguments, dict)
                            else str(tc.arguments),
                        },
                    }
                    if getattr(tc, "extra_content", None):
                        tc_dict["extra_content"] = tc.extra_content
                    elif self.provider_id == "gemini" or "generativelanguage.googleapis.com" in self.base_url:
                        tc_dict["thought_signature"] = "skip_thought_signature_validator"
                        tc_dict["function"]["thought_signature"] = "skip_thought_signature_validator"
                    formatted_tcs.append(tc_dict)
                item["tool_calls"] = formatted_tcs
            if m.tool_call_id:
                item["tool_call_id"] = m.tool_call_id
            if m.role == Role.TOOL:
                resolved_name = m.name or tool_id_to_name.get(m.tool_call_id or "") or "tool_execution"
                item["name"] = resolved_name
            elif m.name:
                item["name"] = m.name
            raw_items.append(item)

        # Second pass: deduplicate multiple tool responses for the same tool_call_id
        formatted = []
        for item in raw_items:
            if item["role"] == "tool":
                cid = item.get("tool_call_id")
                prev_idx = None
                if cid:
                    for i in range(len(formatted) - 1, -1, -1):
                        if formatted[i].get("role") == "tool" and formatted[i].get("tool_call_id") == cid:
                            prev_idx = i
                            break
                        if formatted[i].get("role") == "assistant":
                            break
                if prev_idx is not None:
                    formatted[prev_idx] = item
                else:
                    formatted.append(item)
            else:
                formatted.append(item)

        return formatted

    def _format_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        formatted = []
        for t in tools:
            params = dict(t.parameters) if isinstance(t.parameters, dict) and t.parameters else {"type": "object", "properties": {}}
            if "type" not in params:
                params["type"] = "object"
            if "properties" not in params:
                params["properties"] = {}
            formatted.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": params,
                    },
                }
            )
        return formatted

    def _parse_tool_calls(self, tool_calls_data: Optional[List[Dict[str, Any]]]) -> Optional[List[ToolCall]]:
        if not tool_calls_data:
            return None
        parsed = []
        for tc in tool_calls_data:
            func = tc.get("function", {})
            name = func.get("name", "")
            args_raw = func.get("arguments", "{}")
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw)
                except Exception:
                    args = {"raw": args_raw}
            else:
                args = args_raw or {}
            call_id = tc.get("id") or "call_unknown"
            extra_content = tc.get("extra_content")
            parsed.append(ToolCall(id=call_id, name=name, arguments=args, extra_content=extra_content))
        return parsed or None

    def _build_payload(self, request: CompletionRequest, stream: bool) -> Dict[str, Any]:
        model_name = self._format_model_name(request.model)
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": self._format_messages(request.messages),
            "stream": stream,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        tools = self._format_tools(request.tools)
        if tools:
            payload["tools"] = tools

        return payload

    def _handle_error_status(self, status_code: int, error_text: str):
        if status_code == 401 or status_code == 403:
            raise AuthenticationError(
                f"Authentication failed with provider: {error_text}",
                provider_id=self.provider_id,
            )
        elif status_code == 404:
            raise ModelNotFoundError(
                f"Requested model or endpoint not found: {error_text}",
                provider_id=self.provider_id,
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Provider rate limit exceeded: {error_text}",
                provider_id=self.provider_id,
            )
        else:
            raise GatewayError(
                f"Provider HTTP error {status_code}: {error_text}",
                provider_id=self.provider_id,
            )

    def _extract_retry_delay(self, error_text: str, default: float = 3.0) -> float:
        match = re.search(r"retry(?:Delay[\"']?\s*:\s*[\"']?|\s+in\s+)([\d\.]+)\s*s?", error_text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                return min(max(val, 1.0), 30.0)
            except Exception:
                pass
        return default

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = self._build_payload(request, stream=False)
        url = f"{self.base_url}/chat/completions"
        max_retries = 3

        for attempt in range(max_retries + 1):
            try:
                client = self._get_client()
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                if resp.status_code != 200:
                    self._handle_error_status(resp.status_code, resp.text)

                data = resp.json()
                choices = data.get("choices") or [{}]
                choice = choices[0] if choices else {}
                msg_data = choice.get("message", {})
                content = msg_data.get("content") or ""
                tool_calls = self._parse_tool_calls(msg_data.get("tool_calls"))

                chat_msg = ChatMessage(
                    role=Role.ASSISTANT,
                    content=content,
                    tool_calls=tool_calls,
                )

                usage = data.get("usage")

                return CompletionResponse(
                    model=data.get("model", request.model),
                    message=chat_msg,
                    finish_reason=choice.get("finish_reason", "stop"),
                    usage=usage,
                )

            except RateLimitError as rle:
                if attempt >= max_retries:
                    raise
                delay = self._extract_retry_delay(rle.message, default=float(2 ** attempt * 2))
                logger.warning(
                    "Provider %s rate limit (429) hit. Retrying in %.1fs (attempt %d/%d)...",
                    self.provider_id,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay)
            except (AuthenticationError, ModelNotFoundError):
                raise
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                raise ProviderUnavailableError(
                    f"Failed to connect to OpenAI endpoint at {self.base_url}: {e}",
                    provider_id=self.provider_id,
                ) from e
            except Exception as e:
                raise GatewayError(f"OpenAI completion error: {e}", provider_id=self.provider_id) from e

        raise RateLimitError("Provider rate limit retries exhausted", provider_id=self.provider_id)

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request, stream=True)
        url = f"{self.base_url}/chat/completions"
        max_retries = 3

        for attempt in range(max_retries + 1):
            try:
                client = self._get_client()
                async with client.stream("POST", url, headers=self._get_headers(), json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        self._handle_error_status(response.status_code, err_body.decode("utf-8", errors="replace"))

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data:"):
                            data_str = line[len("data:") :].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            choices = data.get("choices", [])
                            if not choices:
                                continue
                            choice = choices[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content") or ""
                            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
                            finish_reason = choice.get("finish_reason")
                            tool_calls = self._parse_tool_calls(delta.get("tool_calls"))

                            is_finished = finish_reason is not None

                            yield StreamChunk(
                                content=content,
                                reasoning_content=reasoning,
                                tool_calls=tool_calls,
                                finish_reason=finish_reason,
                                is_finished=is_finished,
                                usage=data.get("usage"),
                            )
                return
            except RateLimitError as rle:
                if attempt >= max_retries:
                    raise
                delay = self._extract_retry_delay(rle.message, default=float(2 ** attempt * 2))
                logger.warning(
                    "Provider %s rate limit (429) hit during stream. Retrying in %.1fs (attempt %d/%d)...",
                    self.provider_id,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                await asyncio.sleep(delay)
            except (AuthenticationError, ModelNotFoundError):
                raise
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                raise ProviderUnavailableError(
                    f"Streaming connection failed to OpenAI at {self.base_url}: {e}",
                    provider_id=self.provider_id,
                ) from e
            except Exception as e:
                raise GatewayError(f"OpenAI stream error: {e}", provider_id=self.provider_id) from e

    async def list_models(self) -> List[ModelDescriptor]:
        """Fetch available models from OpenAI-compatible /models endpoint."""
        url = f"{self.base_url}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            client = self._get_client()
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            descriptors: List[ModelDescriptor] = []
            for item in data.get("data", []):
                model_id = item.get("id", "unknown")
                is_vision = "vision" in model_id.lower() or "4o" in model_id.lower()
                descriptors.append(
                    ModelDescriptor(
                        id=f"{self.provider_id}/{model_id}",
                        name=model_id,
                        provider=self.provider_id,
                        param_size_b=None,
                        quantization="server_managed",
                        family=item.get("owned_by", "openai"),
                        is_multimodal=is_vision,
                    )
                )
            return descriptors
        except Exception as e:
            raise ProviderUnavailableError(
                f"Failed to fetch models from OpenAI at {self.base_url}: {e}",
                provider_id=self.provider_id,
            ) from e

    async def close(self) -> None:
        """Gracefully close the underlying HTTP client [REQ-RESIL-002]."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
