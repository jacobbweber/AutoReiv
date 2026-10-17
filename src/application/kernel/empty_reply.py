"""Empty model replies are errors, not chat rows [CARD-475, REQ-475-004/006]."""

from __future__ import annotations

import json
from typing import Any, Iterable, List, Sequence

from src.domain.gateway.models import ChatMessage, Role

EMPTY_REPLY_MESSAGE = "The model returned an empty reply."


def is_empty_reply(content: str | None, tool_calls) -> bool:
    return not (content or "").strip() and not tool_calls


def is_empty_assistant_row(m: ChatMessage) -> bool:
    """An assistant row saved before CARD-475 when a stream failed silently."""
    return m.role == Role.ASSISTANT and is_empty_reply(m.content, m.tool_calls)


def skip_empty_assistant_rows(messages: Iterable[ChatMessage]) -> List[ChatMessage]:
    return [m for m in messages if not is_empty_assistant_row(m)]


def model_history_rows(messages: Iterable[ChatMessage]) -> List[ChatMessage]:
    """Rows the model may see: no empty assistant rows, no chat notes [CARD-482, REQ-482-002]."""
    return [m for m in skip_empty_assistant_rows(messages) if m.role != Role.NOTE]


def chat_note(notice: dict, text: str) -> ChatMessage:
    """A notice kept in the thread as a note row (shown after reloads and on other devices) [CARD-482]."""
    return ChatMessage(role=Role.NOTE, content=text, name=str((notice or {}).get("type") or "notice"))


def latest_user_prompt(user_content: str | None, history: Sequence[Any]) -> str:
    """Return the active user prompt text for the turn from user_content or history."""
    if user_content:
        return user_content
    for hm in reversed(list(history or [])):
        if getattr(hm, "role", None) == Role.USER and getattr(hm, "content", None):
            return str(hm.content)
    return ""


def _turn_tool_messages(history: Sequence[Any]) -> List[Any]:
    """Tool messages since the latest user message in chronological order [CARD-695]."""
    out: List[Any] = []
    for msg in reversed(list(history or [])):
        role = str(getattr(msg, "role", "") or "").lower()
        if role.endswith("user"):
            content = str(getattr(msg, "content", "") or "").strip()
            if not content.startswith("(AutoReiv check)"):
                break
        elif role.endswith("tool"):
            out.append(msg)
    out.reverse()
    return out


def post_tool_empty_fallback(history: Sequence[Any]) -> str:
    """Synthesize a concise completion summary when a model returns empty text after running tools [CARD-695].

    Returns "" when no tool ran in the current turn so initial empty replies still raise EmptyModelReplyError.
    """
    tool_msgs = _turn_tool_messages(history)
    if not tool_msgs:
        return ""

    structured_messages: List[str] = []
    fallback_summaries: List[str] = []
    tool_names: List[str] = []

    for msg in tool_msgs:
        name = str(getattr(msg, "name", "") or "tool").strip()
        if name and name not in tool_names:
            tool_names.append(name)
        raw = str(getattr(msg, "content", "") or "").strip()
        if not raw:
            continue
        if raw.startswith("{"):
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                msg_text = str(parsed.get("message") or "").strip()
                if msg_text:
                    if msg_text not in structured_messages:
                        structured_messages.append(msg_text)
                    continue
                err_text = str(parsed.get("error") or "").strip()
                if err_text:
                    line = f"{name} failed: {err_text}"
                    if line not in fallback_summaries:
                        fallback_summaries.append(line)
                    continue
                if name == "skill_view" and (parsed.get("id") or parsed.get("name")):
                    line = f"Loaded skill '{parsed.get('id') or parsed.get('name')}'."
                    if line not in fallback_summaries:
                        fallback_summaries.append(line)
                    continue
                compact = {
                    k: v
                    for k, v in parsed.items()
                    if k not in ("instructions", "code", "content", "check", "tools", "catalog_tools", "skills")
                }
                summary_str = json.dumps(compact, ensure_ascii=False)
                line = f"Completed `{name}`: {summary_str[:220]}"
                if line not in fallback_summaries:
                    fallback_summaries.append(line)
                continue
        first_line = raw.splitlines()[0].strip()
        line = first_line[:240] if name in first_line else f"Completed `{name}`: {first_line[:220]}"
        if line not in fallback_summaries:
            fallback_summaries.append(line)

    if structured_messages:
        return " ".join(structured_messages)
    if fallback_summaries:
        return " ".join(fallback_summaries[-2:])
    return f"Completed {', '.join(tool_names)}." if tool_names else ""

