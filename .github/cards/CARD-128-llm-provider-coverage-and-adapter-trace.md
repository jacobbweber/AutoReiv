# [CARD-128] LLM provider coverage, research, and adapter trace

> **Status**: In Review
> **Created**: 2026-08-31
> **Spec Reference**: CARD-001; CARD-005; CARD-015; CARD-024; CARD-043
> **Labels**: `type:feat`, `type:gateway`, `type:docs`

---

## 1. Why / Intent

AutoReiv's LLM Gateway must provide complete, verified coverage across top industry LLM providers (both local offline engines and cloud providers) so that switching providers in **Settings Studio** works seamlessly out-of-the-box for chat, autonomous jobs, tool calling, and live model discovery.

Currently:
- Most development testing was performed on **Ollama**.
- **Google Gemini** was missing from presets.
- **LM Studio** was missing a dedicated local preset (default port `1234`).
- **vLLM** needed its own dedicated self-hosted preset (default port `8000`).
- **Anthropic Claude** required native API support.
- Schemas for tool calling, streaming SSE delta chunks, reasoning tokens (`<think>` vs `reasoning_content`), and live model discovery need end-to-end audit and hermetic contract tests for all providers.

---

## 2. What to Build

### 1. Provider Preset Coverage (`src/application/settings/presets.py`)
Establish dedicated presets with default URLs, recommended models, and key requirements:
1. **Ollama (Local)**: `http://127.0.0.1:11434` (Offline, zero setup)
2. **LM Studio (Local)**: `http://127.0.0.1:1234/v1` (Local OpenAI-compatible engine)
3. **vLLM (Self-Hosted)**: `http://127.0.0.1:8000/v1` (High-throughput cluster/local inference)
4. **Google Gemini**: `https://generativelanguage.googleapis.com/v1beta/openai` (Gemini 2.0 Flash, Gemini 1.5 Pro/Flash)
5. **OpenAI**: `https://api.openai.com/v1` (GPT-4o, GPT-4o-mini, o1, o3-mini)
6. **Anthropic Claude**: `https://api.anthropic.com/v1` (Claude 3.7 Sonnet, Claude 3.5 Sonnet, Haiku)
7. **OpenRouter**: `https://openrouter.ai/api/v1` (200+ models via unified gateway)
8. **Groq Cloud**: `https://api.groq.com/openai/v1` (Ultra-low latency LPU inference)
9. **DeepSeek**: `https://api.deepseek.com/v1` (DeepSeek-V3, DeepSeek-R1)
10. **Together AI**: `https://api.together.xyz/v1` (High-throughput open weights)

### 2. Gateway Adapters & Schema Hardening (`src/infrastructure/gateway/`)
- **OpenAI Compatible Adapter (`openai_adapter.py`)**:
  - Request format: system prompt, user/assistant message history, function definitions in `tools` JSON schema.
  - Streaming SSE chunk parsing: `choices[0].delta.content`, `choices[0].delta.tool_calls` index accumulation, `reasoning_content` delta capture.
  - Model discovery: robust parsing of `/v1/models` data arrays across OpenAI, Gemini, LM Studio, vLLM, Groq, DeepSeek, Together, OpenRouter.
- **Ollama Adapter (`ollama_adapter.py`)**:
  - Streaming `/api/chat` with `tools` schema, message history, `<think>` reasoning extraction, `/api/tags` model discovery.
- **Anthropic Adapter (`anthropic_adapter.py`)**:
  - Direct Anthropic Messages API support (`/v1/messages` with `x-api-key`, `anthropic-version: 2023-06-01`, `tools` schema translation) and streaming SSE events.

### 3. Settings Studio & Health Diagnostics
- **Live Model Discovery (`/api/models/discover`)**:
  - Automatically queries the active provider's models endpoint with timeout fallback to curated catalog presets.
- **Connectivity Probing (`test_provider_connectivity`)**:
  - Tests authentication, latency, and available models for the selected provider.
- **Hardware RAM Fit Estimator**:
  - Accurately estimates model footprint for local engines (Ollama, LM Studio, vLLM).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] All 10 provider presets listed in `src/application/settings/presets.py` with valid default URLs and recommended models.
- [x] Google Gemini, LM Studio, and vLLM have dedicated, working presets in Settings Studio.
- [x] Tool calling JSON schemas validated across all adapter types.
- [x] Streaming SSE responses correctly parse content, tool call arguments, and reasoning deltas.
- [x] Live model discovery `/api/models/discover` successfully extracts model lists from standard `/v1/models` and `/api/tags`.
- [x] `test_provider_connectivity` tool accurately probes all supported provider endpoints.
- [x] Comprehensive unit and integration test suite verifies each provider's payload contracts.
- [x] Status In Review after code; local commit only on `qa`, no push.

---

## 4. Constraints & Honor Flags

- Work on `qa`. Do not push. Do not clone.
- Preserve backward compatibility with existing saved settings and SQLite provider records.
- Zero external runtime dependencies beyond standard python libraries already installed.
- Do not start CARD-116 (memory) or CARD-125 (Wiki schema) here.

---

## 5. Walked Lock (2026-08-31)

| Beat | Lock |
|------|------|
| Provider Coverage | 10 Providers: Ollama, LM Studio, vLLM, Gemini, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Together. |
| Local Presets | Dedicated presets for Ollama (`11434`), LM Studio (`1234`), and vLLM (`8000`). |
| Schemas & Tracing | Strict verification for tool calling, streaming deltas, reasoning tokens, and model discovery. |
| Discovery | Resilient `/v1/models` and `/api/tags` parsing with curated preset fallback. |

---

## 6. Pickup

Status is **Ready**. Do not implement until Jacob says **build** / **continue**.
