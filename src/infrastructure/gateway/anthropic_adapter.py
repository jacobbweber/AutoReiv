"""
Anthropic Claude Provider Adapter [REQ-GW-006, CARD-128].
Communicates with Anthropic Messages API (/v1/messages).
Supports Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3.5 Haiku, and tool calling.
"""

import json
import logging
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


class AnthropicProviderAdapter(LLMProviderPort):
    """Adapter for Anthropic Messages API."""

    provider_id: str = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com/v1",
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 60.0,
        provider_id: str = "anthropic",
    ):
        self.provider_id = provider_id
        self.api_key = api_key or ""
        raw_url = (base_url or "https://api.anthropic.com/v1").strip()
        if not raw_url.startswith(("http://", "https://")):
            raw_url = f"https://{raw_url}"
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
        self._client = client

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
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
        if model.startswith("anthropic/"):
            return model[len("anthropic/") :]
        return model

    def _format_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters or {"type": "object", "properties": {}},
            }
            for t in tools
        ]

    def _build_payload(self, request: CompletionRequest, stream: bool) -> Dict[str, Any]:
        system_prompt = ""
        messages = []

        for m in request.messages:
            if m.role == Role.SYSTEM:
                if system_prompt:
                    system_prompt += "\n" + m.content
                else:
                    system_prompt = m.content
            elif m.role == Role.TOOL:
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id or "unknown",
                                "content": m.content,
                            }
                        ],
                    }
                )
            else:
                role_str = "assistant" if m.role == Role.ASSISTANT else "user"
                content_blocks = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                if m.tool_calls:
                    for tc in m.tool_calls:
                        content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc.id,
                                "name": tc.name,
                                "input": tc.arguments if isinstance(tc.arguments, dict) else {},
                            }
                        )
                if content_blocks:
                    messages.append({"role": role_str, "content": content_blocks})

        model_name = self._format_model_name(request.model)
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        tools = self._format_tools(request.tools)
        if tools:
            payload["tools"] = tools

        return payload

    def _handle_error_status(self, status_code: int, error_text: str):
        if status_code in (401, 403):
            raise AuthenticationError(
                f"Anthropic authentication failed: {error_text}",
                provider_id=self.provider_id,
            )
        elif status_code == 404:
            raise ModelNotFoundError(
                f"Anthropic model or endpoint not found: {error_text}",
                provider_id=self.provider_id,
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Anthropic rate limit exceeded: {error_text}",
                provider_id=self.provider_id,
            )
        else:
            raise GatewayError(
                f"Anthropic HTTP error {status_code}: {error_text}",
                provider_id=self.provider_id,
            )

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = self._build_payload(request, stream=False)
        url = f"{self.base_url}/messages"

        try:
            client = self._get_client()
            resp = await client.post(url, headers=self._get_headers(), json=payload)
            if resp.status_code != 200:
                self._handle_error_status(resp.status_code, resp.text)

            data = resp.json()
            content_blocks = data.get("content", [])
            text_parts = []
            tool_calls = []

            for block in content_blocks:
                btype = block.get("type")
                if btype == "text":
                    text_parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.get("id", "tool_unknown"),
                            name=block.get("name", ""),
                            arguments=block.get("input", {}),
                        )
                    )

            full_text = "".join(text_parts)
            chat_msg = ChatMessage(
                role=Role.ASSISTANT,
                content=full_text,
                tool_calls=tool_calls or None,
            )

            return CompletionResponse(
                model=data.get("model", request.model),
                message=chat_msg,
                finish_reason=data.get("stop_reason", "stop"),
                usage=data.get("usage"),
            )

        except (AuthenticationError, ModelNotFoundError, RateLimitError):
            raise
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise ProviderUnavailableError(
                f"Failed to connect to Anthropic endpoint at {self.base_url}: {e}",
                provider_id=self.provider_id,
            ) from e
        except Exception as e:
            raise GatewayError(f"Anthropic completion error: {e}", provider_id=self.provider_id) from e

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request, stream=True)
        url = f"{self.base_url}/messages"

        try:
            client = self._get_client()
            async with client.stream("POST", url, headers=self._get_headers(), json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    self._handle_error_status(response.status_code, err_body.decode("utf-8", errors="replace"))

                current_tool_id = ""
                current_tool_name = ""
                current_tool_args_raw = ""

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[len("data:") :].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("type", "")

                        if event_type == "content_block_start":
                            block = data.get("content_block", {})
                            if block.get("type") == "tool_use":
                                current_tool_id = block.get("id", "")
                                current_tool_name = block.get("name", "")
                                current_tool_args_raw = ""

                        elif event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            dtype = delta.get("type", "")
                            if dtype == "text_delta":
                                yield StreamChunk(
                                    content=delta.get("text", ""),
                                    is_finished=False,
                                )
                            elif dtype == "input_json_delta":
                                current_tool_args_raw += delta.get("partial_json", "")

                        elif event_type == "content_block_stop":
                            if current_tool_name:
                                try:
                                    parsed_args = json.loads(current_tool_args_raw) if current_tool_args_raw else {}
                                except Exception:
                                    parsed_args = {"raw": current_tool_args_raw}
                                yield StreamChunk(
                                    content="",
                                    tool_calls=[
                                        ToolCall(
                                            id=current_tool_id or "tool_call",
                                            name=current_tool_name,
                                            arguments=parsed_args,
                                        )
                                    ],
                                    is_finished=False,
                                )
                                current_tool_id = ""
                                current_tool_name = ""
                                current_tool_args_raw = ""

                        elif event_type == "message_delta":
                            delta = data.get("delta", {})
                            stop_reason = delta.get("stop_reason")
                            yield StreamChunk(
                                content="",
                                finish_reason=stop_reason,
                                is_finished=True,
                                usage=data.get("usage"),
                            )

        except (AuthenticationError, ModelNotFoundError, RateLimitError):
            raise
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise ProviderUnavailableError(
                f"Streaming connection failed to Anthropic at {self.base_url}: {e}",
                provider_id=self.provider_id,
            ) from e
        except Exception as e:
            raise GatewayError(f"Anthropic stream error: {e}", provider_id=self.provider_id) from e

    async def list_models(self) -> List[ModelDescriptor]:
        """Return supported Anthropic Claude model descriptors."""
        claude_models = [
            ("claude-3-7-sonnet-20250219", "Claude 3.7 Sonnet (Hybrid Reasoning)", True),
            ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", True),
            ("claude-3-5-haiku-20241022", "Claude 3.5 Haiku", True),
            ("claude-3-opus-20240229", "Claude 3 Opus", True),
        ]
        return [
            ModelDescriptor(
                id=f"anthropic/{mid}",
                name=mname,
                provider="anthropic",
                param_size_b=None,
                quantization="cloud",
                family="claude",
                is_multimodal=is_vision,
            )
            for mid, mname, is_vision in claude_models
        ]

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
