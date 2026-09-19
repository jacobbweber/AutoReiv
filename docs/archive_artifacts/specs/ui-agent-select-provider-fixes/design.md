# Technical Design: Chat Studio Agent Selection & Provider Model Discovery Fixes

> **Document ID**: `DESIGN-UI-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-UI-001]`, `[REQ-UI-002]`

---

## 1. Architectural Changes

### 1.1 Chat Studio Header Agent Switcher (`[REQ-UI-001]`)
- In `index.html`: Replace static `<h2 id="activeAgentTitle">` text in `#view-chat` top bar with `<select id="chatTopBarAgentSelect">` while keeping a hidden `#activeAgentTitle` for backwards compatibility with export and note titles.
- In `app.js`:
  - `loadAgents()` reads `localStorage.getItem('autoreiv_active_agent_id')`.
  - `switchSelectedAgent(agentId)` synchronizes both `#agentSelect` and `#chatTopBarAgentSelect`, sets `localStorage`, updates `#activeAgentTone`, and calls `loadSessions()`.

### 1.2 Multi-Preset Gateway Model Discovery (`[REQ-UI-002]`)
- In `src/infrastructure/gateway/openai_adapter.py`: Add `provider_id: str = "openai"` to `OpenAIProviderAdapter.__init__`.
- In `src/infrastructure/gateway/ollama_adapter.py`: Add `provider_id: str = "ollama"` to `OllamaProviderAdapter.__init__`.
- In `src/web/app.py`: Pass `provider_id` when constructing adapters in `POST /api/settings/providers` and `GET /api/models/discover`.
- In `src/web/static/app.js`: In `discoverAndPopulateModels()`, ensure `state.savedDefaultModel` is preserved as an option if not already in the discovered models list.
