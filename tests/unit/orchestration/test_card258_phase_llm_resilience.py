"""CARD-258 phase LLM longer budget + retries [REQ-PLLM-001..002]."""

from __future__ import annotations

import asyncio
import os

import pytest

from src.application.orchestration.phase_llm_resilience import (
    STANDING_PHASE_LLM_RETRIES,
    STANDING_PHASE_LLM_TIMEOUT_SECONDS,
    await_phase_llm_with_retry,
    format_phase_llm_exhausted_reason,
    is_phase_llm_retryable,
    load_repo_dotenv,
    resolve_standing_phase_llm_retries,
    resolve_standing_phase_llm_timeout,
)
from src.application.orchestration.research_before_plan import format_job_failed_honesty


# --- REQ-PLLM-001: budget + classify -----------------------------------------


def test_default_budget_longer_than_120s_kill():
    """Default must outlive the 120s Formulate kill (job_cbf0a330fc5c)."""
    # Isolate from operator .env leaking into the process.
    os.environ.pop("STANDING_PHASE_LLM_TIMEOUT_SECONDS", None)
    os.environ.pop("STANDING_PHASE_LLM_RETRIES", None)
    assert STANDING_PHASE_LLM_TIMEOUT_SECONDS >= 240.0
    assert resolve_standing_phase_llm_timeout() >= 240.0
    assert 1 <= STANDING_PHASE_LLM_RETRIES <= 2
    assert 1 <= resolve_standing_phase_llm_retries() <= 2


def test_resolve_timeout_honors_env_at_call_time(monkeypatch):
    monkeypatch.setenv("STANDING_PHASE_LLM_TIMEOUT_SECONDS", "1800")
    assert resolve_standing_phase_llm_timeout() == 1800.0
    monkeypatch.setenv("STANDING_PHASE_LLM_TIMEOUT_SECONDS", "45")
    assert resolve_standing_phase_llm_timeout() == 45.0


def test_resolve_retries_honors_env(monkeypatch):
    monkeypatch.setenv("STANDING_PHASE_LLM_RETRIES", "1")
    assert resolve_standing_phase_llm_retries() == 1
    monkeypatch.setenv("STANDING_PHASE_LLM_RETRIES", "0")
    assert resolve_standing_phase_llm_retries() == 0


def test_is_phase_llm_retryable_timeout_and_stall_only():
    assert is_phase_llm_retryable(asyncio.TimeoutError()) is True
    assert is_phase_llm_retryable(TimeoutError("timed out")) is True
    assert is_phase_llm_retryable(ConnectionResetError("connection reset")) is True
    assert is_phase_llm_retryable(ConnectionError("connection refused")) is True

    class ProviderUnavailableError(Exception):
        pass

    assert is_phase_llm_retryable(ProviderUnavailableError("Streaming connection failed")) is True

    class AuthenticationError(Exception):
        pass

    class ModelNotFoundError(Exception):
        pass

    assert is_phase_llm_retryable(AuthenticationError("401")) is False
    assert is_phase_llm_retryable(ModelNotFoundError("qwen missing")) is False
    assert is_phase_llm_retryable(ValueError("bad packet")) is False
    assert is_phase_llm_retryable(asyncio.CancelledError()) is False


# --- REQ-PLLM-001: retry then success ----------------------------------------


@pytest.mark.asyncio
async def test_retry_on_timeout_then_success():
    calls = {"n": 0}

    async def factory(attempt: int) -> str:
        calls["n"] += 1
        if attempt < 3:
            await asyncio.sleep(1.0)
            return "late"
        return f"ok-{attempt}"

    out = await await_phase_llm_with_retry(factory, timeout_seconds=0.05, retries=2)
    assert out == "ok-3"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retry_on_connection_stall_then_success():
    calls = {"n": 0}

    async def factory(attempt: int) -> str:
        calls["n"] += 1
        if attempt == 1:
            raise ConnectionResetError("connection reset by peer")
        return "recovered"

    out = await await_phase_llm_with_retry(factory, timeout_seconds=1.0, retries=1)
    assert out == "recovered"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_exhausted_retries_raise_timeout():
    async def factory(_attempt: int) -> str:
        await asyncio.sleep(1.0)
        return "never"

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await await_phase_llm_with_retry(factory, timeout_seconds=0.05, retries=1)


@pytest.mark.asyncio
async def test_non_retryable_fails_immediately():
    calls = {"n": 0}

    async def factory(_attempt: int) -> str:
        calls["n"] += 1
        raise ValueError("bad json")

    with pytest.raises(ValueError):
        await await_phase_llm_with_retry(factory, timeout_seconds=1.0, retries=2)
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_on_retry_callback_fires(monkeypatch):
    seen: list[tuple[int, int, str]] = []

    async def factory(attempt: int) -> str:
        if attempt == 1:
            raise ConnectionError("connection stall")
        return "ok"

    def on_retry(attempt: int, attempts: int, reason: str) -> None:
        seen.append((attempt, attempts, reason))

    out = await await_phase_llm_with_retry(
        factory, timeout_seconds=1.0, retries=1, on_retry=on_retry
    )
    assert out == "ok"
    assert seen == [(1, 2, "connection_stall")]


# --- REQ-PLLM-002: exhausted reason + honesty never Done ---------------------


def test_exhausted_reason_and_honesty_never_say_done():
    reason = format_phase_llm_exhausted_reason(
        kind="timeout",
        timeout_s=300.0,
        attempt=3,
        attempts=3,
    )
    assert "phase_llm_timeout" in reason
    assert "retries_exhausted" in reason
    assert "300" in reason
    msg = format_job_failed_honesty(
        job_id="job_cbf0a330fc5c",
        phase_name="Formulate",
        reason=reason,
    )
    assert "FAILED" in msg
    assert "job_cbf0a330fc5c" in msg
    assert "Formulate" in msg
    assert "Not done" in msg
    assert "Done." not in msg
    assert "success criterion met" not in msg.lower()


def test_load_repo_dotenv_does_not_overwrite(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "STANDING_PHASE_LLM_TIMEOUT_SECONDS=999\nALREADY_SET=fromfile\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ALREADY_SET", "keep-me")
    monkeypatch.delenv("STANDING_PHASE_LLM_TIMEOUT_SECONDS", raising=False)
    loaded = load_repo_dotenv(tmp_path)
    assert loaded == tmp_path / ".env"
    assert os.environ["ALREADY_SET"] == "keep-me"
    assert os.environ["STANDING_PHASE_LLM_TIMEOUT_SECONDS"] == "999"
