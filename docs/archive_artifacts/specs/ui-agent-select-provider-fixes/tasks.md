# Tasks Specification: Chat Studio Agent Selection & Provider Model Discovery Fixes

> **Document ID**: `TASKS-UI-001`  
> **Status**: In Progress  
> **Traceability ID**: `[REQ-UI-001]`, `[REQ-UI-002]`

---

## Vertical Slices

- [ ] **Slice 1: Chat Studio Persistent Multi-Surface Agent Switcher**
  - [ ] Task 1.1: `[REQ-UI-001]` Add `#chatTopBarAgentSelect` in `src/web/templates/index.html`.
  - [ ] Task 1.2: `[REQ-UI-001]` Add `switchSelectedAgent()` and `localStorage` persistence in `src/web/static/app.js`.

- [ ] **Slice 2: Multi-Preset Model Discovery & Saved Model Retention**
  - [ ] Task 2.1: `[REQ-UI-002]` Update `OpenAIProviderAdapter` and `OllamaProviderAdapter` constructors to accept custom `provider_id`.
  - [ ] Task 2.2: `[REQ-UI-002]` Update `src/web/app.py` endpoints to pass `provider_id` correctly.
  - [ ] Task 2.3: `[REQ-UI-002]` Update `discoverAndPopulateModels()` and `saveProvidersBtn` in `src/web/static/app.js` to preserve custom/saved models.
  - [ ] Task 2.4: `[REQ-UI-001]` Add unit tests in `tests/unit/web/test_ui_agent_select_and_discovery.py`.
  - [ ] Task 2.5: `[REQ-UI-001]` Run pre-flight DoD quality gates.
