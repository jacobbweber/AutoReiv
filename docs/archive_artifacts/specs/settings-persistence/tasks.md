# Tasks Specification: Provider & Model Settings Persistence

> **Document ID**: `TASKS-SETTINGS-PERSIST-001`  
> **Status**: In Progress  
> **Traceability ID**: `[REQ-SET-007]`, `[REQ-SET-008]`

---

## Vertical Slices

- [ ] **Slice 1: Backend Settings Model Persistence**
  - [ ] Task 1.1: `[REQ-SET-007]` Update `ProviderSettingsRequest` in `src/web/app.py` to include `default_model_id: Optional[str] = "default"`.
  - [ ] Task 1.2: `[REQ-SET-007]` Persist and return `default_model_id` in `POST /api/settings/providers` and `GET /api/settings`.
  - [ ] Task 1.3: `[REQ-SET-007]` Add unit tests in `tests/unit/settings/test_settings_persistence.py` and `tests/unit/web/test_unified_settings_ui.py`.

- [ ] **Slice 2: Frontend Settings Studio Model Hydration & Retention**
  - [ ] Task 2.1: `[REQ-SET-008]` Update `saveProvidersBtn` in `src/web/static/app.js` to send `default_model_id: provModelSelect ? provModelSelect.value : 'default'`.
  - [ ] Task 2.2: `[REQ-SET-008]` Update `loadSettings()` and `discoverAndPopulateModels()` in `src/web/static/app.js` to preserve and restore `provModelSelect` value from `state.savedDefaultModel`.
  - [ ] Task 2.3: `[REQ-SET-008]` Verify end-to-end with pre-flight DoD quality gates.
