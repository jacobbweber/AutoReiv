"""Phase LLM wait/retry policy [CARD-258 / REQ-PLLM-001..002].

Standing Formulate/Execute/Research calls to a local qwen (slow KV fill) must
wait longer than the historical 120s import-time default, and retry 1-2 times
on timeout or connection stall before fail_phase.

Resolve budget at *call time* so operator .env is honored (import-time freeze
was why job_cbf0a330fc5c died at 120s while .env said 1800).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, TypeVar

# Longer than the 120s kill that failed Formulate under qwen KV fill.
# Operator env (STANDING_PHASE_LLM_TIMEOUT_SECONDS) still wins at call time.
STANDING_PHASE_LLM_TIMEOUT_SECONDS = 300.0
# 1-2 retries after the first attempt (Architect lock). 2 = quality over speed.
STANDING_PHASE_LLM_RETRIES = 2

_RETRYABLE_TOKENS = (
    "phase_llm_timeout",
    "timed out",
    "timeout",
    "connection reset",
    "connection aborted",
    "connection closed",
    "connection refused",
    "connection stall",
    "broken pipe",
    "server disconnected",
    "network is unreachable",
    "temporarily unavailable",
    "connect error",
    "read timeout",
    "connect timeout",
    "provider unavailable",
    "streaming connection failed",
)

T = TypeVar("T")


def load_repo_dotenv(start: Optional[Path] = None) -> Optional[Path]:
    """Load repo .env into os.environ without overwriting existing keys.

    Safe to call multiple times. Does not require python-dotenv.
    """
    here = (start or Path.cwd()).resolve()
    candidates = [here, *here.parents]
    env_path: Optional[Path] = None
    for base in candidates:
        probe = base / ".env"
        if probe.is_file() and (base / "pyproject.toml").is_file():
            env_path = probe
            break
    if env_path is None:
        return None
    try:
        raw = env_path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
    return env_path


def resolve_standing_phase_llm_timeout() -> float:
    """Call-time timeout (seconds). Env wins; else module constant (monkeypatchable)."""
    raw = os.environ.get("STANDING_PHASE_LLM_TIMEOUT_SECONDS")
    if raw not in (None, ""):
        try:
            return max(1.0, float(raw))
        except ValueError:
            pass
    return max(1.0, float(STANDING_PHASE_LLM_TIMEOUT_SECONDS))


def resolve_standing_phase_llm_retries() -> int:
    """Call-time retry count (1-2 typical). Env wins; else module constant."""
    raw = os.environ.get("STANDING_PHASE_LLM_RETRIES")
    if raw not in (None, ""):
        try:
            return max(0, min(4, int(raw)))
        except ValueError:
            pass
    return max(0, min(4, int(STANDING_PHASE_LLM_RETRIES)))


def is_phase_llm_retryable(exc: BaseException) -> bool:
    """True for timeout or connection stall — not cancel, auth, or model-missing."""
    if isinstance(exc, asyncio.CancelledError):
        return False
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True
    if isinstance(exc, (ConnectionError, ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
        return True
    name = type(exc).__name__
    if name in {
        "ProviderUnavailableError",
        "TimeoutException",
        "ReadTimeout",
        "ConnectTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "ConnectError",
        "NetworkError",
        "RemoteProtocolError",
        "LocalProtocolError",
    }:
        return True
    # Do not retry auth / missing model even if the message mentions timeout.
    if name in {"AuthenticationError", "ModelNotFoundError"}:
        return False
    msg = str(exc).lower()
    return any(tok in msg for tok in _RETRYABLE_TOKENS)


def format_phase_llm_exhausted_reason(
    *,
    kind: str,
    timeout_s: float,
    attempt: int,
    attempts: int,
    detail: str = "",
) -> str:
    """Honest fail reason after the last attempt. Never implies Done."""
    if kind == "timeout":
        base = f"phase_llm_timeout after {timeout_s}s (attempt {attempt}/{attempts})"
    else:
        extra = f": {detail}" if detail else ""
        base = f"phase_llm_connection_stall (attempt {attempt}/{attempts}){extra}"
    if attempt >= attempts:
        base = f"{base}; retries_exhausted"
    return base


def classify_retry_reason(exc: BaseException) -> str:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "timeout"
    return "connection_stall"


async def await_phase_llm_with_retry(
    factory: Callable[[int], Awaitable[T]],
    *,
    timeout_seconds: Optional[float] = None,
    retries: Optional[int] = None,
    on_retry: Optional[Callable[[int, int, str], Any]] = None,
) -> T:
    """Run factory(attempt) under wait_for; retry timeout/stall; raise last if exhausted.

    factory receives the 1-based attempt index so callers can tag prompts.
    on_retry(attempt, attempts, reason) is invoked *before* the next attempt.
    """
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else resolve_standing_phase_llm_timeout()
    )
    retry_n = int(retries) if retries is not None else resolve_standing_phase_llm_retries()
    attempts = 1 + max(0, retry_n)
    last_exc: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            return await asyncio.wait_for(factory(attempt), timeout=timeout)
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            last_exc = exc
            if (not is_phase_llm_retryable(exc)) or attempt >= attempts:
                raise
            if on_retry is not None:
                maybe = on_retry(attempt, attempts, classify_retry_reason(exc))
                if asyncio.iscoroutine(maybe) or isinstance(maybe, Awaitable):
                    await maybe  # type: ignore[misc]
    assert last_exc is not None
    raise last_exc
