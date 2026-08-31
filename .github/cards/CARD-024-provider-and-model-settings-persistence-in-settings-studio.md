# [CARD-024] Provider and Model Settings Persistence in Settings Studio

> **Status**: Ready
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/settings-persistence/`
> **Labels**: `type:bug`, `milestone:24`, `domain:settings`

---

_Parked 2026-08-29 board hygiene. Not in flight. Provider persist later covered in Settings work; leftover bugs stay here._

## 1. Why / Intent
When the user configures a provider (e.g. Ollama, OpenAI, etc.) and selects an active model (e.g. `llama3.8`, `llama3.2:1b`, `qwen2.5:7b`) in Settings Studio and clicks `Save Provider`, the system fails to persist and restore their model choice. This causes the model selection to reset back to "Auto-Select Default" on every save or page refresh.

---

## 2. What to Build
1. **Backend Model & Provider Settings Contract (`[REQ-SET-007]`)**:
   - Update `ProviderSettingsRequest` to include `default_model_id: Optional[str] = None`.
   - In `POST /api/settings/providers`:
     - Persist `default_model_id` in SQLite `provider_settings`.
     - Update `gateway.default_model_id` and update `settings_service.get_purpose_matrix().default_model` with the chosen model.
   - In `GET /api/settings`:
     - Return `default_model_id` inside the `providers` configuration payload.
2. **Frontend Settings Studio Persistence & Hydration (`[REQ-SET-008]`)**:
   - In `src/web/static/app.js`:
     - Update `saveProvidersBtn` to include `default_model_id: provModelSelect ? provModelSelect.value : 'default'` in the `POST /api/settings/providers` payload.
     - Store `state.savedDefaultModel` in client state and keep it updated when the user changes `provModelSelect`.
     - In `discoverAndPopulateModels()`, preserve and restore `provModelSelect.value = state.savedDefaultModel`.
     - In `loadSettings()`, hydrate `state.savedDefaultModel = data.providers.default_model_id || data.matrix.default_model || 'default'` and populate both the provider preset, host, key, and active model.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-SET-007]`: `POST /api/settings/providers` saves and `GET /api/settings` returns `default_model_id`.
- [ ] `[REQ-SET-008]`: Selecting a model in Settings Studio and clicking `Save Provider` retains and restores that model choice across saves and page reloads.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.
- [ ] Pre-flight DoD passes via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Zero breaking changes to existing passing tests.
- Single isolated branch cut from `qa`.
