"""CARD-567: bounded model replies (tokens and wall-clock seconds per streaming model call).

Resolution: setting ``reply_limits`` ({"max_tokens": int, "max_seconds": int}) > env ``AUTOREIV_MAX_REPLY_TOKENS`` /
``AUTOREIV_MAX_REPLY_SECONDS`` > defaults. Without a limit Ollama's num_predict defaults to unbounded and vLLM generates up
to the rest of the context window; the adapters' read timeout only bounds silence between chunks.

CARD-592: the same setting also holds the other model-call waits, all generous because local models fill the KV cache,
think for a long time and queue behind other chats:

- ``provider_idle_seconds``: how long a provider may send nothing (before the first byte and between chunks).
- ``phase_seconds``: one job phase / developer turn / routine model call.
- ``helper_seconds``: one short helper call (capability analysis, distillation, Skill Studio drafts).

Each resolves setting > env > default. ``bind_store`` lets code without a store handle (phase and helper calls) read
the saved setting.

CARD-605: ``wiki_lookups_per_reply`` (wiki searches / note lists one reply may make; 1-50, default 8) lives here too,
read at the start of every reply.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Tuple

DEFAULT_MAX_TOKENS = 32768  # CARD-586: generous (thinking counts toward it), never unbounded
DEFAULT_MAX_SECONDS = 7200  # CARD-592: 2 h, counted from the model's first token (CARD-585 had 20 min)
DEFAULT_PROVIDER_IDLE_SECONDS = 1800  # CARD-592: 30 min of provider silence (CARD-588 had 15 min)
DEFAULT_PHASE_SECONDS = 21600  # CARD-592: 6 h per job phase / developer turn / routine call (was 300 s)
DEFAULT_HELPER_SECONDS = 1800  # CARD-592: 30 min per helper call (was 4-60 s)
SETTING_KEY = "reply_limits"
# setting field -> env override, default
TIMEOUT_FIELDS = {
    "provider_idle_seconds": ("AUTOREIV_PROVIDER_IDLE_SECONDS", DEFAULT_PROVIDER_IDLE_SECONDS),
    "phase_seconds": ("STANDING_PHASE_LLM_TIMEOUT_SECONDS", DEFAULT_PHASE_SECONDS),
    "helper_seconds": ("AUTOREIV_HELPER_CALL_SECONDS", DEFAULT_HELPER_SECONDS),
}
DEFAULT_WIKI_LOOKUPS = 8  # CARD-605 (Jacob 2026-10-03: 8, was 4)
WIKI_LOOKUPS_MIN = 1
WIKI_LOOKUPS_MAX = 50
WIKI_LOOKUPS_FIELD = "wiki_lookups_per_reply"
WIKI_LOOKUPS_ENV = "AUTOREIV_WIKI_LOOKUPS_PER_REPLY"
_bound_store: Any = None
MIN_TOKENS = 1024
# CARD-586: helper calls (memory, detection, planning, Teach) ask for a few hundred tokens; a thinking model spends that
# before it answers, so non-streaming calls get at least this much room. CARD-591: 4096 cut 4 of 22 nemotron helper
# calls (finish_reason length) on 2026-09-30, so 16384 (still at most a quarter of the window).
HELPER_MIN_TOKENS = 16384


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


def bind_store(store: Any) -> None:
    """CARD-592: remember the settings store so phase and helper calls can read the saved limits."""
    global _bound_store
    _bound_store = store


def _saved(store: Any = None) -> dict:
    store = store if store is not None else _bound_store
    if store is None:
        return {}
    try:
        raw = store.get_setting(SETTING_KEY)
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def saved_timeout(field: str, store: Any = None) -> Optional[int]:
    """The saved value of one CARD-592 field, or None when the operator has not set it."""
    return _positive_int(_saved(store).get(field))


def resolve_timeout(field: str, store: Any = None) -> int:
    """One CARD-592 field: setting > env > default."""
    env_key, default = TIMEOUT_FIELDS[field]
    return saved_timeout(field, store) or _positive_int(os.environ.get(env_key)) or default


def resolve_all_limits(store: Any = None) -> dict:
    """Every Reply limits value, for the Settings API."""
    tokens, seconds = resolve_reply_limits(store)
    out = {"max_tokens": tokens, "max_seconds": seconds}
    for field in TIMEOUT_FIELDS:
        out[field] = resolve_timeout(field, store)
    out[WIKI_LOOKUPS_FIELD] = resolve_wiki_lookups(store)
    return out


def _in_wiki_range(value: Any) -> Optional[int]:
    n = _positive_int(value)
    return n if n is not None and WIKI_LOOKUPS_MIN <= n <= WIKI_LOOKUPS_MAX else None


def resolve_wiki_lookups(store: Any = None) -> int:
    """CARD-605: wiki look-ups allowed in one reply: setting > env > default 8 (values outside 1-50 are ignored)."""
    return (
        _in_wiki_range(_saved(store).get(WIKI_LOOKUPS_FIELD))
        or _in_wiki_range(os.environ.get(WIKI_LOOKUPS_ENV))
        or DEFAULT_WIKI_LOOKUPS
    )


def helper_call_seconds() -> float:
    """CARD-592: timeout for one short helper model call (bound store > env > default)."""
    return float(resolve_timeout("helper_seconds"))


def resolve_reply_limits(store: Any = None) -> Tuple[int, int]:
    """(max_tokens, max_seconds) from the setting, then env, then defaults."""
    saved = _saved(store) if store is not None else {}
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
        f"Stopped: the model was still generating after the time limit of {max_seconds} s for one reply "
        "(counted from its first token). "
        "Try again, ask for a smaller step, or raise the limit (Settings: reply_limits.max_seconds)."
    )
