# [CARD-156] Per-Agent LLM Endpoint Credentials and Live Model Discovery

> **Status**: In Review
> **Created**: 2026-09-04
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings`

---

## 1. Why / Intent

In Settings Studio, users can configure an LLM provider's API Base URL, API Key, and click "Refresh Models" to discover available models live.

In Agent Studio, when a user changes an agent's LLM Provider from "Use Global Default" to a specific provider (e.g. OpenRouter, DeepSeek, or an alternative Ollama instance), the agent currently has no way to provide custom endpoint credentials (API Base URL, API Key) or trigger live model discovery. The Model dropdown remains stuck on "Use Global Default" with an empty list.

To make per-agent provider selection fully functional:
- When an agent's **LLM Provider** is set to a specific provider (not "Use Global Default"), Agent Studio reveals the same configuration options as Settings Studio: **API Base URL**, **API Key / Token**, and a **[ 🔄 Refresh Models ]** discovery button.
- Clicking **Refresh Models** discovers live models from that specific endpoint and immediately populates the agent's Model dropdown.
- When set back to "Use Global Default", the extra fields collapse, keeping the agent sheet clean and inheriting global Settings.

---

## 2. What to Build

1. **Agent Studio UI (`src/web/templates/index.html`)**:
   - Inside `#view-agents`, below `#forgeProviderSelect`, add `#forgeProviderConfigContainer` (hidden when provider is `default`):
     - **API Base URL** (`#forgeApiBaseUrlInput`): Endpoint URL, automatically prefilled with the chosen provider's standard URL preset.
     - **API Key / Token** (`#forgeApiKeyInput`): Secure input for API token.
     - **Refresh Models Button** (`#forgeDiscoverModelsBtn`): Placed above or beside `#forgeAgentModelSelect` to trigger live discovery.
     - **Context Window (tokens)** (`#forgeContextWindowInput`): Optional numeric context token limit.
2. **Frontend Interaction (`src/web/static/modules/studios/forge.js`)**:
   - Toggle visibility of `#forgeProviderConfigContainer` based on whether `#forgeProviderSelect` is `default`.
   - On provider change: prefill `#forgeApiBaseUrlInput` from `PRESETS_DEFAULTS`.
   - Wire `#forgeDiscoverModelsBtn`: Calls `/api/models/discover` with `provider_id`, `host_url`, and `api_key`, then dynamically refreshes `#forgeAgentModelSelect`.
   - Include `api_base_url`, `api_key`, and `context_window` in agent save payload.
3. **Model Discovery Endpoint (`src/web/routers/settings.py` / `models.py`)**:
   - Update `/api/models/discover` to accept query params or JSON body: `provider_id`, `base_url`, `api_key` for on-demand discovery without mutating global settings.
4. **Domain & Persistence (`src/domain/kernel/models.py`, `src/domain/settings/models.py`, `src/infrastructure/memory/`)**:
   - Add `api_base_url: Optional[str] = None`, `api_key: Optional[str] = None`, `context_window: Optional[int] = None` to `AgentProfile` and `AgentCustomization`.
   - Add database column migrations for `custom_agents` and `agent_overrides` tables.
   - Update repository save/load methods to store and retrieve these fields.
5. **Kernel Model Execution (`src/application/kernel/agent_kernel.py`)**:
   - When calling LLM gateway for an agent, pass agent-specific `api_base_url` and `api_key` if configured, overriding global settings.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-AGENT-LLM-001]`: Selecting a non-default provider in Agent Studio reveals API Base URL, API Key, Context Window, and Refresh Models controls.
- [x] `[REQ-AGENT-LLM-002]`: Selecting "Use Global Default" hides the per-agent endpoint fields and inherits from Settings Studio.
- [x] `[REQ-AGENT-LLM-003]`: Clicking "Refresh Models" in Agent Studio fetches live models using the agent's entered provider, URL, and API key.
- [x] `[REQ-AGENT-LLM-004]`: Saving an agent persists `api_base_url`, `api_key`, and `context_window` in `custom_agents` / `agent_overrides`.
- [x] `[REQ-AGENT-LLM-005]`: Agent execution uses the agent-specific endpoint and credentials when configured.
- [x] `[REQ-AGENT-LLM-006]`: Automated tests pass cleanly via `pytest` (707 passed) and `npm run test:unit:frontend` (25/25 files passed).
- [x] `[REQ-AGENT-LLM-007]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing agents or global default configuration.
- Password fields must not expose keys in plain text.
- Follow "How we walk cards with Jacob" rules.
- Local `qa` branch is source of truth.

