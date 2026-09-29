---
id: CARD-580
title: "Provider connectivity check probes OLLAMA_HOST (0.0.0.0) instead of the configured providers"
status: In Review
created: 2026-09-29
branch: fix/card-580-provider-connectivity-default
related:
  - CARD-211
labels:
  - type:bug
  - area:observability
  - P2
needs_decision: none
milestone: M24
---

# [CARD-580] Provider connectivity check probes OLLAMA_HOST (0.0.0.0) instead of the configured providers

> **Status**: In Review
> **Labels**: `type:bug`, `area:observability`, `P2`

## Why

Found in the 2026-09-29 battery test (throwaway :8770, AutoReiv platform-health skill on Spark). `test_provider_connectivity`
with no arguments defaulted to `provider_id="ollama"` and, with no legacy `ollama_host` key, used the `OLLAMA_HOST`
environment variable. On Jarvis that is `0.0.0.0` (a bind address, no port), so the check reported
`http://0.0.0.0 ... WinError 10049` and never looked at the real default (vLLM on Spark) or the Developer's own Nimo
override. It also ignored the per-provider `providers.<id>.base_url` that Settings saves (CARD-211).

## Change

- `src/application/skills/system_agent_tools.py`: with no arguments the tool probes the configured default provider and
  each per-agent model override (`agent_model_settings`: provider, api_base_url, model). URL order: saved
  `providers.<id>.base_url`, legacy keys, preset default, then `OLLAMA_HOST`. Bind addresses (`0.0.0.0`, `::`) become
  `127.0.0.1`; Ollama gets port 11434 when none is given. Results carry `endpoint_source`; API keys come from the vault
  credential first. Error bodies are capped at 500 characters.
- Tests `tests/unit/skills/test_card580_provider_connectivity.py` (8, all fail on the old code); the old coverage test no
  longer accepts `0.0.0.0` as a valid endpoint.

## Acceptance

- [x] No-argument check probes the default provider (Spark `/v1/models`) and the Developer override (Nimo `/api/tags`).
- [x] `OLLAMA_HOST=0.0.0.0` never produces a `0.0.0.0` probe.

## Log

- 2026-09-29: fixed on the branch with tests.
