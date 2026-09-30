---
id: CARD-588
title: "Provider read timeout survives a swap-gateway model load (900 s); timeout errors say what happened"
status: In Review
created: 2026-09-29
branch: card/588-provider-timeout-swap
related:
  - CARD-584
  - CARD-585
labels:
  - type:bug
  - area:gateway
  - P2
needs_decision: none
milestone: M24
---

# [CARD-588] Provider read timeout survives a swap-gateway model load (900 s); timeout errors say what happened

> **Status**: In Review
> **Labels**: `type:bug`, `area:gateway`, `P2`

## Why

2026-09-29 live test of CARD-584 on the throwaway :8770: the Spark gateway (:8099) is a swap gateway that loads one
model at a time; a swap took ~5 min. The first Direct request during a swap failed after 200 s with
`[vllm] Streaming connection failed to OpenAI at ...: ` (empty reason): the OpenAI adapter read timeout was 200 s and
`str(httpx.ReadTimeout)` is empty. Jacob prefers relaxed limits (function over restriction).

## Change

- New `src/infrastructure/gateway/timeouts.py`: `DEFAULT_PROVIDER_READ_TIMEOUT = 900` s (read timeout = longest silence
  from the provider, not the reply length), `provider_read_timeout()` (env `GATEWAY_DEFAULT_TIMEOUT_SECONDS`
  overrides), `describe_http_error()` (never empty: `ReadTimeout: no data from the provider for N s (model may be
  loading or swapping)`).
- OpenAI, Anthropic and Ollama adapters default to it (OpenAI was 200 s, Ollama 600 s); the factory default and the
  Settings-built Ollama provider no longer pin 200 s. Stream error messages use `describe_http_error`.
- The per-reply time limit (CARD-585: 1200 s from the first token) is unchanged and still bounds a running reply.

## Acceptance

- [x] Default 900 s for all adapters and the factory; env override; explicit timeout kept.
- [x] A stream ReadTimeout error names the timeout (tests `tests/unit/gateway/test_card588_provider_timeout.py`).
- [ ] Live: a request sent during a gateway swap waits for the model instead of failing at 200 s (see Log).

## Log

- 2026-09-29: built on the branch with tests; old 200 s/600 s default tests updated to 900 s.
