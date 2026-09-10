# [CARD-214] Per-Agent LLM Provider Resolution and Gemini Model Quota Fallback

> **Status**: Ready
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:gateway`, `domain:kernel`, `domain:agents`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Per-Agent Provider Independence**:
   - When an operator configures an agent in **Agent Studio** (`#view-agents`) to use a specific LLM Provider (e.g. Ollama), chatting with that agent in **Chat Studio** (`#view-chat`) must always route to that agent's provider—even if the agent's model dropdown is left on "Use Global Default" (`default`).
   - If an agent is left on "Platform Default", it continues to use the platform provider selected in **Settings Studio** (e.g. Google Gemini).
2. **Resilience Against Model Quota Exhaustion**:
   - If a Gemini model hits its free-tier daily request quota (`HTTP 429: Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash`), the system should automatically fall back to an active, responsive model (`gemini-3.7-flash` or `gemini-3.1-flash-lite-preview`) without silently failing.

---

### Beat 2: What AutoReiv Does Now
1. **Cascade Bug in `_resolve_model`** (`src/application/kernel/agent_kernel.py`):
   - When an agent has `provider = "ollama"` and `model = "default"`, the resolution logic skips the agent's provider override because `model == "default"`. It falls through to the global platform provider settings, resolving to the platform's default model (e.g. `gemini-3.6-flash`). The agent's custom provider setting is completely ignored.
2. **Gemini 20 Requests/Day Free Tier Quota Exhaustion**:
   - `gemini-3.6-flash` has a hard 20-request/day limit on Google AI Studio's free tier. Jacob's key reached this limit, causing Google to return `HTTP 429 RESOURCE_EXHAUSTED`.
   - Meanwhile, `gemini-3.7-flash` and `gemini-3.1-flash-lite-preview` have separate available quotas and respond in milliseconds.
3. **Stale Running Server**:
   - The background web server process was started prior to recent card commits and has not reloaded the latest gateway sanitization code in memory.

---

### Beat 3: What Will Change
1. **Per-Agent Provider Model Resolution Fix** (`src/application/kernel/agent_kernel.py`):
   - In `_resolve_model(agent)`:
     - When an agent has an explicit provider (e.g. `ollama`) and its model is `default`:
       - Lookup that provider's configured model in `provider_settings` (`providers[provider]["default_model_id"]`).
       - If none is configured, return `{provider}/default`.
       - NEVER fall through to another provider's platform default model.
2. **Gemini Default Model Recommendation & Quota Resiliency**:
   - In `src/application/settings/presets.py`, set `gemini-3.7-flash` as the top recommended default model to avoid the 20 req/day limit on `gemini-3.6-flash`.
   - In `src/infrastructure/gateway/openai_adapter.py`: on HTTP 429 quota exhaustion specifically for Gemini models, retry or fallback to alternative compatible models (`gemini-3.7-flash`, `gemini-3.1-flash-lite-preview`).
   - Update stored settings in the live SQLite database to use `gemini-3.7-flash`.
3. **Dynamic Vault Key Resolution on Boot** (`src/web/app.py`):
   - Respect `vault_cred_id` when loading provider keys on server startup rather than hardcoding `llm-provider-{p_id}`.
4. **Automated Unit & Integration Tests**:
   - Add unit tests verifying:
     - Agent with `provider="ollama"`, `model="default"` resolves to Ollama, not Gemini.
     - Agent with `provider="default"` resolves to the active platform provider.

---

## 2. Acceptance Criteria (Definition of Done)
- [ ] **AC-1 (Per-Agent Resolution)**: When an agent's provider is set to `ollama` (or any non-default provider) and its model is `default`, the kernel resolves the model and provider to that agent's provider, not the platform provider.
- [ ] **AC-2 (Platform Provider Inheritance)**: When an agent's provider is `default`, it resolves to the platform default provider from Settings Studio.
- [ ] **AC-3 (Gemini 3.7 Recommendation & Quota Resiliency)**: Preset and active platform settings recommend and use `gemini-3.7-flash`.
- [ ] **AC-4 (All Quality Gates Green)**: Pytest, Vitest, ESLint, Ruff, Playwright, and RTM preflight checks all pass.

---

## 3. Constraints & Invariants
- Follow the 5 Hard Invariants from AGENTS.md.
- Feature branch `feat/per-agent-provider-resolution` cut from `qa`.
- Card stays `Ready` until Jacob says **build**.
