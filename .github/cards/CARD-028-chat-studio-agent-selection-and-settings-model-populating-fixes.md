# [CARD-028] Chat Studio Agent Selection and Settings Provider Model Discovery Fixes

> **Status**: In Progress
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/ui-agent-select-provider-fixes/`
> **Labels**: `type:bugfix`, `milestone:28`, `domain:ui`

---

## 1. Why / Intent
1. **Chat Studio Agent Selection**: Users switching agents in Chat Studio experienced the agent selection resetting to default upon reload or tab change. Furthermore, there was no direct agent selector dropdown in the Chat top bar header, requiring users (especially on mobile) to rely on the off-canvas drawer.
2. **LLM Provider Settings & Model Discovery**: When selecting a preset (such as OpenAI, Anthropic, DeepSeek, Groq, or vLLM), model discovery failed to populate because `OpenAIProviderAdapter` defaulted its internal `provider_id` to `"openai"`, causing `gateway.list_models(provider_id=pid)` to return empty. Additionally, saved custom model strings were not retained if model discovery was in-flight or returned empty.

---

## 2. What to Build
1. **Chat Studio Persistent & Multi-Surface Agent Switcher (`[REQ-UI-001]`)**:
   - Add `#chatTopBarAgentSelect` dropdown directly in the Chat Studio top header.
   - Synchronize two-way between sidebar `#agentSelect` and topbar `#chatTopBarAgentSelect`.
   - Persist active agent choice in `localStorage` (`autoreiv_active_agent_id`) so it survives page reloads and tab navigation.
   - Prevent `loadAgents()` from forcibly resetting `state.selectedAgentId` to `agents[0].id`.
2. **Provider Model Discovery & Custom Saved Model Retention (`[REQ-UI-002]`)**:
   - Ensure `OpenAIProviderAdapter` and `OllamaProviderAdapter` accept custom `provider_id` parameter so multi-provider presets (`deepseek`, `groq`, `anthropic`, `vllm`, etc.) register correctly in Gateway.
   - Ensure `discoverAndPopulateModels()` preserves and appends the user's saved default model (`state.savedDefaultModel`) in `#provModelSelect` and purpose matrix dropdowns even if the remote provider is offline or returning a custom list.
   - Ensure `POST /api/settings/providers` merges and persists settings without wiping existing provider configuration keys.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-UI-001]`: Chat Studio renders topbar agent selector, synchronizes with sidebar, and persists agent selection in `localStorage`.
- [ ] `[REQ-UI-002]`: Provider adapters accept dynamic `provider_id`, enabling model discovery across all presets; saved models are preserved in dropdowns.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.
- [ ] Pre-flight DoD passes via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
