# Implementation Tasks: Settings Studio & Hardware Fit Calculator

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-SETTINGS-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Settings Domain Models & Schemas
- [x] **Task 1.1** `[REQ-SETTINGS-001]`, `[REQ-SETTINGS-002]`, `[REQ-SETTINGS-004]`: [RED] Write failing unit tests in `tests/unit/settings/test_settings_models.py` verifying `ModelDescriptor`, `ModelPurpose`, `ModelPurposeMatrix`, `HardwareSpecs`, and `ModelFitReport`.
- [x] **Task 1.2** `[REQ-SETTINGS-001]`, `[REQ-SETTINGS-002]`, `[REQ-SETTINGS-004]`: [GREEN] Implement `src/domain/settings/models.py`.

### Slice 2: SQLite Settings & Agent Overrides Store
- [x] **Task 2.1** `[REQ-SETTINGS-006]`, `[REQ-SETTINGS-005]`: [RED] Write failing unit tests in `tests/unit/settings/test_settings_persistence.py` for settings key-value CRUD and agent override persistence.
- [x] **Task 2.2** `[REQ-SETTINGS-006]`, `[REQ-SETTINGS-005]`: [GREEN] Update `src/infrastructure/memory/sqlite_store.py` with `settings` and `agent_overrides` tables and repository methods.

### Slice 3: Live Model Discovery in Adapters & Gateway
- [x] **Task 3.1** `[REQ-SETTINGS-001]`: [RED] Write failing unit tests in `tests/unit/settings/test_model_discovery.py` for Ollama `/api/tags` and OpenAI `/v1/models` discovery.
- [x] **Task 3.2** `[REQ-SETTINGS-001]`: [GREEN] Implement `list_models()` on `LLMProviderPort`, `OllamaProviderAdapter`, `OpenAIProviderAdapter`, and `MultiProviderGateway`.

### Slice 4: Hardware Fit Calculator Engine
- [x] **Task 4.1** `[REQ-SETTINGS-003]`, `[REQ-SETTINGS-004]`: [RED] Write failing unit tests in `tests/unit/settings/test_hardware_calculator.py` for auto-detection and RAM fit calculations across quant levels.
- [x] **Task 4.2** `[REQ-SETTINGS-003]`, `[REQ-SETTINGS-004]`: [GREEN] Implement `HardwareFitCalculator` in `src/application/settings/hardware_calculator.py`.

### Slice 5: Purpose Matrix & Agent Settings Manager
- [x] **Task 5.1** `[REQ-SETTINGS-002]`, `[REQ-SETTINGS-005]`: [RED] Write failing unit tests in `tests/unit/settings/test_agent_settings_manager.py` for purpose routing and dynamic agent tone/system prompt overrides.
- [x] **Task 5.2** `[REQ-SETTINGS-002]`, `[REQ-SETTINGS-005]`: [GREEN] Implement `SettingsService` in `src/application/settings/settings_service.py`.

### Slice 6: Verification, Traceability, & QA Gate
- [x] **Task 6.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 6.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 6.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
