"""
Ollama Provider Adapter [REQ-GW-003].
Communicates with Ollama REST API (/api/chat) for streaming and non-streaming inference.
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from src.application.gateway.ports import LLMProviderPort
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


class OllamaProviderAdapter(LLMProviderPort):
    """Adapter for local/LAN Ollama endpoints."""

    provider_id: str = "ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    def _format_model_name(self, model: str) -> str:
        """Strip provider prefix if present (e.g. 'ollama/qwen2.5:7b' -> 'qwen2.5:7b')."""
        if model.startswith("ollama/"):
            return model[len("ollama/") :]
        return model

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

        try:
            client = self._get_client()
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
