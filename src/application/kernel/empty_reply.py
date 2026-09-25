"""Empty model replies are errors, not chat rows [CARD-475, REQ-475-004/006]."""

from __future__ import annotations

from typing import Iterable, List

from src.domain.gateway.models import ChatMessage, Role

EMPTY_REPLY_MESSAGE = "The model returned an empty reply."


def is_empty_reply(content: str | None, tool_calls) -> bool:
    return not (content or "").strip() and not tool_calls


def is_empty_assistant_row(m: ChatMessage) -> bool:
    """An assistant row saved before CARD-475 when a stream failed silently."""
    return m.role == Role.ASSISTANT and is_empty_reply(m.content, m.tool_calls)


def skip_empty_assistant_rows(messages: Iterable[ChatMessage]) -> List[ChatMessage]:
    return [m for m in messages if not is_empty_assistant_row(m)]
