# ADR-0025: Provider & Model Settings Persistence

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Context**: Milestone 24 (`CARD-024`)  
> **Requirements**: `[REQ-SET-007]`, `[REQ-SET-008]`

---

## Context
When human operators select a provider and model in Settings Studio, their model selection wasn't captured in the provider save request or restored upon reloading the view.

---

## Decision
1. **Model Persistence in Provider Settings**:
   - `ProviderSettingsRequest` includes `default_model_id`.
   - Persisted in SQLite `provider_settings` and synchronized with Gateway & Purpose Matrix default model.
2. **Deterministic UI Hydration**:
   - Client tracks `state.savedDefaultModel`, includes it in `Save Provider` payloads, and restores `provModelSelect.value` after dynamic catalog queries.

---

## Consequences
- Model selection persists seamlessly across saves and refreshes.
