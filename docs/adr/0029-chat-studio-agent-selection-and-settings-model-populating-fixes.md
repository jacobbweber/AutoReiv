# ADR-0029: Chat Studio Agent Selection & Provider Model Discovery Fixes

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Context**: Milestone 28 (`CARD-028`)  
> **Requirements**: `[REQ-UI-001]`, `[REQ-UI-002]`

---

## Context
1. In Chat Studio, switching agents was only possible in the left sidebar, which was hidden on mobile. Upon page load or tab navigation, the selected agent reset to default.
2. In Settings Studio, discovering models for presets other than `ollama` failed because `OpenAIProviderAdapter` registered with hardcoded `provider_id="openai"`, causing lookup mismatches. Saved model choices were also lost if provider model discovery returned empty.

---

## Decision
1. Introduce a synchronized `#chatTopBarAgentSelect` in the Chat Studio top header and persist the active agent ID in browser `localStorage`.
2. Allow `OpenAIProviderAdapter` and `OllamaProviderAdapter` to take a dynamic `provider_id` parameter, ensuring all presets register and discover models correctly.
3. Ensure `discoverAndPopulateModels()` preserves custom and saved model strings in all dropdowns even if the remote host is unreachable or lists a subset of models.

---

## Consequences
- Seamless mobile and desktop agent switching directly inside Chat Studio.
- Multi-provider model discovery and settings persistence operate reliably across all presets.
