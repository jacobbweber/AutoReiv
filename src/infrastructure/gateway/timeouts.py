"""CARD-588: how long a provider may stay silent (between bytes, and before the first byte), and readable errors.

The Spark gateway is a swap gateway: asking for a model that is not loaded unloads the current one and loads the new one
before the first byte (about 5 minutes on 2026-09-29). The old 200 s read timeout failed that first reply with an empty
reason ("Streaming connection failed to OpenAI at ...: " - httpx timeouts have an empty message).

CARD-592: 30 min by default (local models fill the KV cache, think and queue behind other chats), resolved per request:
the saved Settings > Reply limits value (via ``set_provider_idle_resolver``) > env > default. Connect stays short enough
to report a dead host; write and pool waits are generous because a busy host can queue the request body.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

import httpx

DEFAULT_PROVIDER_READ_TIMEOUT = 1800.0
ENV_KEY = "AUTOREIV_PROVIDER_IDLE_SECONDS"
LEGACY_ENV_KEY = "GATEWAY_DEFAULT_TIMEOUT_SECONDS"
CONNECT_TIMEOUT = 60.0
WRITE_TIMEOUT = 600.0
POOL_TIMEOUT = 600.0
PROBE_TIMEOUT = 15.0  # health / model-list probes stay short

_resolver: Optional[Callable[[], Optional[float]]] = None


def set_provider_idle_resolver(resolver: Optional[Callable[[], Optional[float]]]) -> None:
    """Wire the saved setting (Settings > Reply limits > provider_idle_seconds); None when unset."""
    global _resolver
    _resolver = resolver


def _env_seconds(key: str) -> float:
    try:
        value = float(os.environ.get(key, "") or 0)
    except ValueError:
        value = 0.0
    return value if value > 0 else 0.0


def provider_read_timeout() -> float:
    """Seconds of provider silence allowed: saved setting > env (new, then legacy) > 1800."""
    if _resolver is not None:
        try:
            saved = _resolver()
        except Exception:
            saved = None
        if saved and saved > 0:
            return float(saved)
    return _env_seconds(ENV_KEY) or _env_seconds(LEGACY_ENV_KEY) or DEFAULT_PROVIDER_READ_TIMEOUT


def http_timeout(read: Optional[float] = None) -> httpx.Timeout:
    """Timeouts for one model call: generous read/write/pool, short-ish connect."""
    return httpx.Timeout(
        connect=CONNECT_TIMEOUT,
        read=read if read else provider_read_timeout(),
        write=WRITE_TIMEOUT,
        pool=POOL_TIMEOUT,
    )


def probe_timeout() -> httpx.Timeout:
    """Timeouts for a health or model-list probe."""
    return httpx.Timeout(PROBE_TIMEOUT)


def describe_http_error(exc: BaseException, timeout: Optional[float] = None) -> str:
    """Never an empty reason: the exception type, and for timeouts how long the provider was silent."""
    name = type(exc).__name__
    if isinstance(exc, httpx.TimeoutException):
        if isinstance(exc, httpx.ConnectTimeout):
            return f"{name}: could not connect in time"
        waited = f" for {timeout:.0f} s" if timeout else ""
        return f"{name}: no data from the provider{waited} (a model that is still loading can take minutes)"
    text = str(exc).strip()
    return f"{name}: {text}" if text else name
