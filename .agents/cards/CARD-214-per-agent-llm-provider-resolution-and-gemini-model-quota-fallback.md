---
id: CARD-214
title: 'Per-Agent LLM Provider Resolution and Transparent Rate Limit Surfacing'
status: Done
created: 2026-09-10
completed: 2026-09-19
adr: none
labels:
  - type:bugfix
  - domain:gateway
  - domain:kernel
  - domain:agents
---

# [CARD-214] Per-Agent LLM Provider Resolution and Transparent Rate Limit Surfacing

> **Status**: Done  
> **Created**: 2026-09-10  
> **Completed**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:bugfix`, `domain:gateway`, `domain:kernel`, `domain:agents`

---

## 1. The Four Beats

### Beat 1: What Jacob Means

1. **Clean 2-Tier Provider Hierarchy**:
   - The system-level provider and model configured in Settings Studio serves as the single global default for all agents.
   - Any agent can optionally override the system default by setting its own provider/model in Agent Studio.
   - When an agent's provider is set to `"default"` (or omitted), it cleanly inherits the system default provider and model.
   - When an agent specifies an explicit provider (e.g. `ollama`), chatting with that agent in Chat Studio must strictly route to that provider—even if the agent's model dropdown is left on `"default"`. Under no circumstances should an agent's explicit provider be silently hijacked by the global platform provider.
2. **Zero Gemini Hardcoding**:
   - AutoReiv must not hardcode or bias toward Gemini as a default. System providers are user-configured during initial setup, with local Ollama as the local offline baseline.
3. **Transparent Rate Limit Surfacing Across All Providers**:
   - When any LLM provider (Ollama, Gemini, OpenAI, Anthropic, OpenRouter, Groq, etc.) encounters an `HTTP 429` rate limit or quota ceiling (`RateLimitError`), the system must not attempt complex model-switching fallbacks or hang in multi-second sleep loops.
   - Instead, the rate limit must be caught cleanly, surfaced with an informative explanation directly in the chat turn, recorded in the session message history, and halted cleanly.

---

### Beat 2: What AutoReiv Does Now

1. **Cascade Bug in `_resolve_model`** (`src/application/kernel/agent_kernel.py`):
   - In `_resolve_model(agent)`: When an agent has `provider = "ollama"` and `model = "default"`, the inner check `raw_agent_model.lower() != "default"` fails. Execution falls through to line 406 (`state_store.get_setting("provider_settings")`), resolving to the global platform provider's model (e.g. Gemini). The agent's custom provider choice is completely ignored.
2. **Hanging Sleep Loops on Quota Ceilings**:
   - In `src/infrastructure/gateway/openai_adapter.py` and `openai_stream_tool_calls.py`, HTTP 429 triggers 3 backoff sleep attempts (up to 14+ seconds). On daily quota exhaustion (e.g. Google free-tier 20 req/day limit), retrying is futile and hangs the operator's chat before ultimately failing.
3. **Hardcoded Boot Vault Lookup**:
   - `src/web/app.py` loads credentials on startup strictly via `f"llm-provider-{p_id}"`, ignoring custom `vault_cred_id` fields stored in provider settings.

---

### Beat 3: What Will Change

1. **2-Tier Provider Model Resolution** (`src/application/kernel/agent_kernel.py`):
   - In `_resolve_model(agent)`:
     - If `agent.provider` is set and `!= "default"`:
       - If `agent.model` is not `"default"`, return the model (or `{provider}/{model}`).
       - If `agent.model` is `"default"`, look up that provider's default model in `provider_settings["providers"][provider]["default_model_id"]`. If none is configured, return `{provider}/default`.
       - Never fall through to the platform provider when an explicit agent provider is configured.
     - If `agent.provider` is `"default"` or empty:
       - Inherit `default_model_id` and `default_provider_id` from Settings Studio's `provider_settings`.
2. **Unified Rate Limit Handling Across All Providers** (`agent_kernel.py`, `openai_adapter.py`, `anthropic_adapter.py`, `openai_stream_tool_calls.py`):
   - In stream tool calls / completion adapters: if an HTTP 429 response contains quota exhaustion indicators (`RESOURCE_EXHAUSTED`, `quota`, `exceeded`), bypass futile backoff retries and immediately raise `RateLimitError`.
   - In `agent_kernel.py`: catch `RateLimitError` during turn streaming, yield a formatted `KernelEvent` displaying the provider rate limit details directly in chat, save the message into session history, and gracefully finish the turn.
3. **Dynamic Vault Key Resolution on Boot** (`src/web/app.py`):
   - Respect `saved.get("vault_cred_id") or f"llm-provider-{p_id}"` when resolving credentials during server boot.
4. **Automated Unit & Integration Tests**:
   - Verify agent provider override with `model="default"` resolves to the agent's provider.
   - Verify agent with `provider="default"` inherits platform default.
   - Verify rate limits across providers yield a clean, human-readable chat message without hanging.

---

### Beat 4: What Dies Today (The Prune List)

1. **The Provider Hijack Fallthrough**: Delete the code branch in `_resolve_model()` where an explicit provider selection falls through to the platform default provider.
2. **Dead 429 Quota Sleeps**: Eliminate useless backoff retries for daily `RESOURCE_EXHAUSTED` quota errors where sleeping provides zero recovery.
3. **Hardcoded Credential Key IDs in Server Boot**: Remove the inflexible `f"llm-provider-{p_id}"` assumption in `app.py`.

---

## 2. Acceptance Criteria (EARS Format)

- [x] **AC-1 (Per-Agent Explicit Provider Resolution)**: Where an agent has an explicit provider (e.g. `ollama`) and its model is `"default"`, the kernel shall resolve the model and provider to that agent's provider and never fall through to the global platform provider.
- [x] **AC-2 (Platform Provider Inheritance)**: Where an agent has `provider="default"` or omitted, the kernel shall inherit the system default provider and model from Settings Studio.
- [x] **AC-3 (Transparent Rate Limit Surfacing)**: Where any LLM provider returns an HTTP 429 or rate limit error, the system shall surface a clear rate limit explanation directly into the chat message without unhandled crashes or secret model substitutions.
- [x] **AC-4 (Fast Quota Error Return)**: Where a rate limit response indicates permanent or daily quota exhaustion (`RESOURCE_EXHAUSTED`), the adapter shall bypass useless sleep retries and raise immediately.
- [x] **AC-5 (Dynamic Boot Vault Resolution)**: When the server initializes, it shall load provider API credentials respecting `vault_cred_id` from provider settings.
- [x] **AC-6 (Full Preflight Green)**: All 6 preflight gates (`npm run preflight`) and working-tree boundary checks pass cleanly.
