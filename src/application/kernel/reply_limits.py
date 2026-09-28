"""CARD-567: bounded model replies (tokens and wall-clock seconds per streaming model call).

Resolution: setting ``reply_limits`` ({"max_tokens": int, "max_seconds": int}) > env ``AUTOREIV_MAX_REPLY_TOKENS`` /
``AUTOREIV_MAX_REPLY_SECONDS`` > defaults. Without a limit Ollama's num_predict defaults to unbounded and vLLM generates up
to the rest of the context window; the adapters' read timeout only bounds silence between chunks.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple

DEFAULT_MAX_TOKENS = 16384
DEFAULT_MAX_SECONDS = 600
SETTING_KEY = "reply_limits"
MIN_TOKENS = 1024


class ReplyLimitStop(Exception):
    """The model call hit a reply limit; ``message`` is shown to the operator and saved in the chat."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _positive_int(value: Any) -> Optional[int]:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def resolve_reply_limits(store: Any = None) -> Tuple[int, int]:
    """(max_tokens, max_seconds) from the setting, then env, then defaults."""
    saved: dict = {}
    if store is not None:
        try:
            raw = store.get_setting(SETTING_KEY)
        except Exception:
            raw = None
        if isinstance(raw, dict):
            saved = raw
    tokens = (
        _positive_int(saved.get("max_tokens"))
        or _positive_int(os.environ.get("AUTOREIV_MAX_REPLY_TOKENS"))
        or DEFAULT_MAX_TOKENS
    )
    seconds = (
        _positive_int(saved.get("max_seconds"))
        or _positive_int(os.environ.get("AUTOREIV_MAX_REPLY_SECONDS"))
        or DEFAULT_MAX_SECONDS
    )
    return tokens, seconds


def reply_token_limit(max_tokens: int, context_limit: Optional[int]) -> int:
    """Cap at a quarter of the window: compaction keeps the prompt under 75%, so vLLM never rejects prompt + max_tokens."""
    if context_limit and context_limit > 0:
        return max(1, min(max_tokens, max(MIN_TOKENS, context_limit // 4)))
    return max_tokens


def token_limit_message(max_tokens: int, answered: bool) -> str:
    if answered:
        return f"(Reply cut: the model reached the reply limit of {max_tokens} tokens. Setting: reply_limits.max_tokens.)"
    return (
        f"Stopped: the model reached the reply limit of {max_tokens} tokens while still thinking, before it answered. "
        "Try again, ask for a smaller step, or raise the limit (Settings: reply_limits.max_tokens)."
    )


def time_limit_message(max_seconds: int) -> str:
    return (
        f"Stopped: the model was still generating after the time limit of {max_seconds} s for one reply. "
        "Try again, ask for a smaller step, or raise the limit (Settings: reply_limits.max_seconds)."
    )
