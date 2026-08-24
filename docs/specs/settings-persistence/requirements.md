# Requirements Specification: Provider & Model Settings Persistence

> **Document ID**: `SPEC-SETTINGS-PERSIST-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-SET-007]`, `[REQ-SET-008]`

---

## 1. User Story

**As a** system administrator and human operator of AutoReiv,  
**I want** my chosen AI provider and default active model selection to persist reliably when saving in Settings Studio,  
**So that** my preferred local or cloud model remains active across restarts and page refreshes.

---

## 2. EARS Requirements

### [REQ-SET-007] Provider & Model Settings Schema Persistence (State-Driven)
When a user posts provider configuration to `POST /api/settings/providers` with a `default_model_id`, the system SHALL persist `default_model_id` in SQLite, update the global gateway fallback model, and return `default_model_id` in `GET /api/settings`.

### [REQ-SET-008] Settings Studio Model Hydration & Retention (Event-Driven)
When the user selects a model in the `provModelSelect` dropdown and clicks `Save Provider`, the web client SHALL include the selected model in the save payload, preserve the selection during dynamic catalog discovery, and restore the selected model on subsequent visits to Settings Studio.
