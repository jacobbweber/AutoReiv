"""CARD-274: accumulate OpenAI/vLLM streamed tool_call argument fragments by index."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from src.domain.gateway.errors import (
    AuthenticationError,
    GatewayError,
    ModelNotFoundError,
    ProviderUnavailableError,
    RateLimitError,
)
from src.domain.gateway.models import CompletionRequest, StreamChunk, ToolCall

logger = logging.getLogger(__name__)


def accumulate_stream_tool_call_delta(
    pending: Dict[int, Dict[str, Any]],
    tool_calls_data: Optional[List[Dict[str, Any]]],
) -> None:
    """Merge OpenAI/vLLM tool_call SSE deltas by index (CARD-274)."""
    if not tool_calls_data:
        return
    for tc in tool_calls_data:
        idx = tc.get("index", 0)
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = 0
        acc = pending.get(idx)
        if acc is None:
            acc = {
                "id": None,
                "type": "function",
                "function": {"name": "", "arguments": ""},
                "extra_content": None,
            }
            pending[idx] = acc
        if tc.get("id"):
            acc["id"] = tc["id"]
        if tc.get("type"):
            acc["type"] = tc["type"]
        if tc.get("extra_content") is not None:
            acc["extra_content"] = tc["extra_content"]
        func = tc.get("function") or {}
        if func.get("name"):
            acc["function"]["name"] = func["name"]
        if "arguments" in func and func["arguments"] is not None:
            arg_piece = func["arguments"]
            if isinstance(arg_piece, dict):
                acc["function"]["arguments"] = json.dumps(arg_piece)
            else:
                acc["function"]["arguments"] = (acc["function"].get("arguments") or "") + str(arg_piece)


def finalize_pending_stream_tool_calls(
    pending: Dict[int, Dict[str, Any]],
    parse_tool_calls,
) -> Optional[List[ToolCall]]:
    """Parse accumulated stream tool calls once into ToolCall list (CARD-274)."""
    if not pending:
        return None
    ordered = [pending[i] for i in sorted(pending.keys())]
    for tc in ordered:
        if not tc.get("id"):
            tc["id"] = "call_unknown"
    return parse_tool_calls(ordered)


async def stream_with_accumulated_tool_calls(adapter, request: CompletionRequest) -> AsyncIterator[StreamChunk]:
    """OpenAIProviderAdapter.stream replacement that merges tool_call deltas by index."""
    import asyncio
    import httpx

    payload = adapter._build_payload(request, stream=True)
    url = f"{adapter.base_url}/chat/completions"
    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            client = adapter._get_client()
            async with client.stream("POST", url, headers=adapter._get_headers(), json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    adapter._handle_error_status(response.status_code, err_body.decode("utf-8", errors="replace"))

                pending_tool_calls: Dict[int, Dict[str, Any]] = {}
                emitted_final_tools = False

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
                        accumulate_stream_tool_call_delta(pending_tool_calls, delta.get("tool_calls"))

                        is_finished = finish_reason is not None
                        tool_calls = None
                        if is_finished and pending_tool_calls and not emitted_final_tools:
                            tool_calls = finalize_pending_stream_tool_calls(
                                pending_tool_calls, adapter._parse_tool_calls
                            )
                            pending_tool_calls.clear()
                            emitted_final_tools = True

                        if not content and not reasoning and not is_finished and tool_calls is None:
                            continue

                        yield StreamChunk(
                            content=content,
                            reasoning_content=reasoning,
                            tool_calls=tool_calls,
                            finish_reason=finish_reason,
                            is_finished=is_finished,
                            usage=data.get("usage"),
                        )

                if pending_tool_calls and not emitted_final_tools:
                    tool_calls = finalize_pending_stream_tool_calls(
                        pending_tool_calls, adapter._parse_tool_calls
                    )
                    pending_tool_calls.clear()
                    yield StreamChunk(
                        content="",
                        reasoning_content="",
                        tool_calls=tool_calls,
                        finish_reason="tool_calls",
                        is_finished=True,
                        usage=None,
                    )
            return
        except RateLimitError as rle:
            if attempt >= max_retries:
                raise
            delay = adapter._extract_retry_delay(rle.message, default=float(2 ** attempt * 2))
            logger.warning(
                "Provider %s rate limit (429) hit during stream. Retrying in %.1fs (attempt %d/%d)...",
                adapter.provider_id,
                delay,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(delay)
        except (AuthenticationError, ModelNotFoundError):
            raise
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            raise ProviderUnavailableError(
                f"Streaming connection failed to OpenAI at {adapter.base_url}: {e}",
                provider_id=adapter.provider_id,
            ) from e
        except Exception as e:
            raise GatewayError(f"OpenAI stream error: {e}", provider_id=adapter.provider_id) from e
