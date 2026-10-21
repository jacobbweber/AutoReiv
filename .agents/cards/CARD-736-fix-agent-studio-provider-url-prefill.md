---
id: CARD-736
title: "Fix Agent Studio provider URL prefill and surface model discovery errors"
type: bug
status: Done
priority: P2
milestone: M32
needs_decision: none
proof:
  journeys: [card-736-fix-agent-studio-provider-url-prefill]
  checks:
    - tests/unit/settings/test_card736_agent_studio_model_discovery.py
    - tests/unit/frontend/agent_studio_discovery_736.test.js
branch: feat/card-736-fix-agent-studio-provider-url-prefill
log: {minutes: 20, qa_runs: 2, findings: 0}
created: 2026-10-20
---

# CARD-736 Fix Agent Studio provider URL prefill and surface model discovery errors

## Problem
When the global default LLM provider in Settings is `vllm` (e.g. on Spark) and the operator has a saved `ollama` provider URL (e.g. `http://192.168.1.29:11434` on Nimo), opening **Agent Studio → Overrides → LLM Provider & Model Routing** and switching **LLM Provider** to `ollama`:
1. Pre-fills **API Base URL** with `http://127.0.0.1:11434` from `PRESETS_DEFAULTS` instead of the operator's saved `ollama` host from `provider_settings`.
2. When clicking **Refresh Models** (`#forgeDiscoverModelsBtn`) against an unreachable host (such as `127.0.0.1:11434` inside the container or a mistyped IP like `192.268.1.29`), `GET /api/models/discover` catches the connection failure and returns 5 static fallback preset models (`llama3.2:1b`, `llama3.2:3b`, `qwen2.5-coder:7b`, `deepseek-r1:8b`, `mistral:7b`) with no error metadata, causing Agent Studio to show a misleading green toast (`"Discovered 5 model(s) for ollama"`) and populate fake preset models as if they came from the server.
3. Probing a temporary `host_url` in `GET /api/models/discover` calls `gateway.register_provider(adapter)` without restoring the existing registered provider, clobbering the live global provider adapter on `gateway` even when the user has not saved Settings or the probe URL is invalid.

## Cause
1. [`setupAgentModelConfig`](file:///home/spark/autoreiv/src/web/static/modules/studios/forge/config.js#L536-L557) and [`fillForgeForm`](file:///home/spark/autoreiv/src/web/static/modules/studios/forge.js#L323-L327) only look up `PRESETS_DEFAULTS[p].url` (`http://127.0.0.1:11434`) instead of checking saved `provider_settings` from `/api/settings`, and switching `#forgeProviderSelect` does not trigger `discoverModelsForAgent()`.
2. [`discover_models`](file:///home/spark/autoreiv/src/web/routers/settings.py#L410-L529) does not include `using_fallback_presets` or `discovery_error` in its response when `list_models()` raises an exception, nor does it fall back to the saved `provider_settings.providers[pid].base_url` when `target_url` is omitted for a non-default provider.
3. [`discover_models`](file:///home/spark/autoreiv/src/web/routers/settings.py#L441-L450) unconditionally executes `gateway.register_provider(adapter)` whenever `target_url` is passed without restoring the previous registered adapter, mutating the live `gateway` singleton during a read-only discovery probe.

## Change
1. Update [`discover_models`](file:///home/spark/autoreiv/src/web/routers/settings.py) to resolve saved `provider_settings.providers[pid].base_url` when `target_url` is omitted for a non-default provider, restore the previously registered `gateway._providers[pid]` adapter in `finally` after a temporary discovery probe, and return `using_fallback_presets: bool` and `discovery_error: Optional[str]` in the JSON payload.
2. Update [`src/web/static/modules/studios/forge/config.js`](file:///home/spark/autoreiv/src/web/static/modules/studios/forge/config.js) and [`src/web/static/modules/studios/forge.js`](file:///home/spark/autoreiv/src/web/static/modules/studios/forge.js) to resolve saved per-provider `base_url` from `/api/settings` (`getDefaultProviderBaseUrl`), pre-fill `#forgeApiBaseUrlInput` with the saved URL when switching providers, auto-run `discoverModelsForAgent()` on provider change, send `X-Provider-Api-Key` header instead of query string, and surface a warning toast + `(preset — host unreachable)` option label when `using_fallback_presets` / `discovery_error` is returned.
3. Update [`src/web/static/modules/studios/settings.js`](file:///home/spark/autoreiv/src/web/static/modules/studios/settings.js) (`discoverAndPopulateModels`) to show the failure reason in `#modelDiscoveryStatus` when `data.discovery_error` is present.

## What dies
- Permanent overwrite of `gateway._providers[pid]` inside `GET /api/models/discover` when probing a temporary `host_url`.
- `?api_key=` query parameter in `discoverModelsForAgent()` (replaced by `X-Provider-Api-Key` request header).
- Blind green success toast in `discoverModelsForAgent()` when `GET /api/models/discover` fell back to static presets.

## Proof
- Journey `card-736-fix-agent-studio-provider-url-prefill`:
  1. Configures a saved `ollama` provider URL in `provider_settings` while `vllm` is the active default provider.
  2. Opens Agent Studio → Overrides, switches `#forgeProviderSelect` to `ollama`, asserts `#forgeApiBaseUrlInput` pre-fills with the saved `ollama` URL rather than `http://127.0.0.1:11434`, and auto-discovers the live models from that server.
  3. Enters an unreachable URL in `#forgeApiBaseUrlInput`, clicks `#forgeDiscoverModelsBtn`, and asserts a warning toast with the connection error is displayed rather than a green success toast.
- Checks:
  - `tests/unit/settings/test_card736_agent_studio_model_discovery.py`: asserts `GET /api/models/discover` returns `using_fallback_presets: True` and `discovery_error` on connection failure, does NOT overwrite the live registered provider on `app.state.gateway`, and resolves saved `provider_settings.providers[pid].base_url` when `host_url` is omitted.
  - `tests/unit/frontend/agent_studio_discovery_736.test.js`: asserts `getDefaultProviderBaseUrl` prefers saved provider `base_url` over `PRESETS_DEFAULTS`, switching `#forgeProviderSelect` pre-fills the saved URL and triggers live discovery, and `discoverModelsForAgent` shows a warning toast on `using_fallback_presets`.

## Plan and decisions
- Approved by Jacob (`1. Recommended`):
  1. Pre-fill Agent Studio's **API Base URL** from saved `provider_settings` before falling back to `PRESETS_DEFAULTS`, and auto-discover models when switching providers in Agent Studio.
  2. Include `discovery_error` and `using_fallback_presets` in `/api/models/discover` (keeping HTTP 200 + `models` for backward compatibility with offline fallback tests) and surface a warning toast/status in Agent Studio and Settings Studio when discovery falls back to presets.
  3. Probe temporary `host_url` overrides in `/api/models/discover` without clobbering the global `gateway` provider registration.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-736-fix-agent-studio-provider-url-prefill` | desktop | PASS | Saved Ollama URL pre-filled and live `qwen3.8:latest` discovered; unreachable host showed warning toast and `(preset — host unreachable)` options |
| `card-736-fix-agent-studio-provider-url-prefill` | phone | PASS | Saved Ollama URL pre-filled and live `qwen3.8:latest` discovered; unreachable host showed warning toast and `(preset — host unreachable)` options |

Screenshots:
- `/tmp/autoreiv-qa/card-736/card-736-fix-agent-studio-provider-url-prefill-desktop-01-configure-saved-ollama-url-while-keeping-global-.png`
- `/tmp/autoreiv-qa/card-736/card-736-fix-agent-studio-provider-url-prefill-desktop-02-unreachable-host-url-in-agent-studio-surfaces-wa.png`
- `/tmp/autoreiv-qa/card-736/card-736-fix-agent-studio-provider-url-prefill-phone-02-unreachable-host-url-in-agent-studio-surfaces-wa.png`

## Release note
- Fixed Agent Studio LLM Provider Overrides so selecting a provider pre-fills its saved Base URL from Settings, auto-refreshes live models without overwriting the global gateway provider, and surfaces connection errors instead of silently displaying static preset models as live.
