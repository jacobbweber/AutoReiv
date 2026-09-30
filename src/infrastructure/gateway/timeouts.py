"""CARD-588: how long a provider may stay silent (between bytes, and before the first byte), and readable errors.

The Spark gateway is a swap gateway: asking for a model that is not loaded unloads the current one and loads the new one
before the first byte (about 5 minutes on 2026-09-29). The old 200 s read timeout failed that first reply with an empty
reason ("Streaming connection failed to OpenAI at ...: " - httpx timeouts have an empty message).
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

DEFAULT_PROVIDER_READ_TIMEOUT = 900.0
ENV_KEY = "GATEWAY_DEFAULT_TIMEOUT_SECONDS"


def provider_read_timeout() -> float:
    """Seconds of provider silence allowed: env GATEWAY_DEFAULT_TIMEOUT_SECONDS, else 900."""
    try:
        value = float(os.environ.get(ENV_KEY, "") or 0)
    except ValueError:
        value = 0.0
    return value if value > 0 else DEFAULT_PROVIDER_READ_TIMEOUT


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
