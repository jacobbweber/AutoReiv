"""
Ollama Provider Adapter [REQ-GW-003].
Communicates with Ollama REST API (/api/chat) for streaming and non-streaming inference.
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from src.application.gateway.ports import LLMProviderPort
from src.application.kernel.context_compactor import get_model_context_limit
from src.domain.gateway.errors import (
    GatewayError,
    ModelNotFoundError,
    ProviderUnavailableError,
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


class OllamaProviderAdapter(LLMProviderPort):
    """Adapter for local/LAN Ollama endpoints."""

    provider_id: str = "ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 180.0,
        provider_id: str = "ollama",
    ):

        self.provider_id = provider_id
        raw_url = (base_url or "http://127.0.0.1:11434").strip()
        if not raw_url.startswith(("http://", "https://")):
            raw_url = f"http://{raw_url}"
        raw_url = raw_url.replace("://0.0.0.0", "://127.0.0.1")
        if raw_url in ("http://127.0.0.1", "http://localhost"):
            raw_url = f"{raw_url}:11434"
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self.default_model = "llama3.2:latest"
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)
        self._client = client
        self._client_injected = client is not None

    def _http_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(connect=30.0, read=self.timeout, write=30.0, pool=15.0)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._http_timeout(),
                limits=self.limits,
            )
        return self._client

    def _format_model_name(self, model: str) -> str:
        """Strip provider prefix if present (e.g. 'ollama/qwen2.5:7b' -> 'qwen2.5:7b'), resolving 'default'."""
        clean = (model or "default").strip()
        if clean.startswith("ollama/"):
            clean = clean[len("ollama/") :]
        if clean in ("default", ""):
            clean = getattr(self, "default_model", "llama3.2:latest") or "llama3.2:latest"
        return clean

    def _format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for m in messages:
            item: Dict[str, Any] = {
                "role": m.role.value,
                "content": m.content,
            }
            if m.tool_calls:
                item["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in m.tool_calls
                ]
            formatted.append(item)
        return formatted

    def _format_tools(self, tools: Optional[List[ToolDefinition]]) -> Optional[List[Dict[str, Any]]]:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def _parse_tool_calls(self, tool_calls_data: Optional[List[Dict[str, Any]]]) -> Optional[List[ToolCall]]:
        if not tool_calls_data:
            return None
        parsed = []
        for idx, tc in enumerate(tool_calls_data):
            func = tc.get("function", {})
            name = func.get("name", "")
            args = func.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"raw": args}
            call_id = tc.get("id") or f"ollama_call_{idx}"
            parsed.append(ToolCall(id=call_id, name=name, arguments=args))
        return parsed or None

    def _build_payload(self, request: CompletionRequest, stream: bool) -> Dict[str, Any]:
        model_name = self._format_model_name(request.model)
        payload: Dict[str, Any] = {
            "model": model_name,
            "messages": self._format_messages(request.messages),
            "stream": stream,
            "options": {
                "temperature": request.temperature,
                "num_ctx": request.num_ctx or get_model_context_limit(model_name),
            },
        }
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens

        tools = self._format_tools(request.tools)
        if tools:
            payload["tools"] = tools

        return payload

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        payload = self._build_payload(request, stream=False)
        url = f"{self.base_url}/api/chat"

        owned_client: Optional[httpx.AsyncClient] = None
        try:
            if self._client_injected:
                client = self._get_client()
            else:
                owned_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self._http_timeout(),
                    limits=self.limits,
                )
                client = owned_client
            resp = await client.post(url, json=payload)
            if resp.status_code == 404:
                raise ModelNotFoundError(
                    f"Model '{request.model}' not found on Ollama server: {resp.text}",
                    provider_id=self.provider_id,
                )
            resp.raise_for_status()
            data = resp.json()

            msg_data = data.get("message", {})
            role_str = msg_data.get("role", "assistant")
            content = msg_data.get("content", "")
            tool_calls = self._parse_tool_calls(msg_data.get("tool_calls"))

            chat_msg = ChatMessage(
                role=Role(role_str) if role_str in Role.__members__.values() else Role.ASSISTANT,
                content=content,
                tool_calls=tool_calls,
            )

            usage = None
            if "prompt_eval_count" in data or "eval_count" in data:
                usage = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                }

            return CompletionResponse(
                model=data.get("model", request.model),
                message=chat_msg,
                finish_reason=data.get("done_reason") or ("stop" if data.get("done") else "unknown"),
                usage=usage,
            )

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise ProviderUnavailableError(
                f"Failed to connect to Ollama at {self.base_url}: {e}",
                provider_id=self.provider_id,
            ) from e
        except ModelNotFoundError:
            raise
        except Exception as e:
            raise GatewayError(f"Ollama execution error: {e}", provider_id=self.provider_id) from e
        finally:
            if owned_client is not None:
                await owned_client.aclose()

    async def stream(self, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request, stream=True)
        url = f"{self.base_url}/api/chat"

        try:
            client = self._get_client()
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code == 404:
                    err_body = await response.aread()
                    raise ModelNotFoundError(
                        f"Model '{request.model}' not found on Ollama server: {err_body.decode('utf-8', errors='replace')}",
                        provider_id=self.provider_id,
                    )
                response.raise_for_status()

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    done = data.get("done", False)
                    msg = data.get("message", {})
                    content = msg.get("content", "")
                    tool_calls = self._parse_tool_calls(msg.get("tool_calls"))

                    yield StreamChunk(
                        content=content,
                        tool_calls=tool_calls,
                        finish_reason=data.get("done_reason") or ("stop" if done else None),
                        is_finished=done,
                    )

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise ProviderUnavailableError(
                f"Streaming connection failed to Ollama at {self.base_url}: {e}",
                provider_id=self.provider_id,
            ) from e
        except ModelNotFoundError:
            raise
        except Exception as e:
            raise GatewayError(f"Ollama stream error: {e}", provider_id=self.provider_id) from e

    async def list_models(self) -> List[ModelDescriptor]:
        """Fetch available models from Ollama /api/tags."""
        url = f"{self.base_url}/api/tags"
        try:
            client = self._get_client()
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            descriptors: List[ModelDescriptor] = []
            for item in data.get("models", []):
                name = item.get("name") or item.get("model", "unknown")
                details = item.get("details", {})
                param_str = details.get("parameter_size", "")
                param_val = None
                if param_str:
                    clean = param_str.upper().replace("B", "").strip()
                    try:
                        param_val = float(clean)
                    except ValueError:
                        param_val = None

                quant = details.get("quantization_level", "Q4_K_M")
                family = details.get("family", "unknown")
                is_vision = "vision" in name.lower() or "llava" in name.lower()

                descriptors.append(
                    ModelDescriptor(
                        id=f"{self.provider_id}/{name}",
                        name=name,
                        provider=self.provider_id,
                        param_size_b=param_val,
                        quantization=quant,
                        family=family,
                        is_multimodal=is_vision,
                    )
                )
            if descriptors:
                self.default_model = descriptors[0].name
            return descriptors
        except Exception as e:
            raise ProviderUnavailableError(
                f"Failed to fetch models from Ollama at {self.base_url}: {e}",
                provider_id=self.provider_id,
            ) from e

    async def close(self) -> None:
        """Gracefully close the underlying HTTP client [REQ-RESIL-002]."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


OllamaAdapter = OllamaProviderAdapter
