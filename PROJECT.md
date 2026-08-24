# Project: AutoReiv Code Audit & Quality Remediation

## Architecture
- **Web / Presentation Layer**: FastAPI backend (`src/web/app.py`, ~53 endpoints), Vanilla SPA frontend (`src/web/templates/index.html`, `src/web/static/app.js`, Tailwind CSS, Feather Icons, Mermaid.js).
- **Application Layer**: Use-case orchestrators and ports (`src/application/kernel/`, `src/application/gateway/`, `src/application/orchestration/`, `src/application/settings/`, `src/application/skills/`).
- **Domain Layer**: Core business models and entities (`src/domain/agents/`, `src/domain/gateway/`, `src/domain/memory/`, `src/domain/observability/`, `src/domain/routines/`, `src/domain/telemetry/`, `src/domain/wiki/`).
- **Infrastructure Layer**: SQLite persistence with WAL mode (`src/infrastructure/storage/sqlite_store.py`), Ollama & OpenAI adapters (`src/infrastructure/gateway/`), Builtin Agent Registry (`src/infrastructure/agents/`).
- **CLI & Entry points**: `src/cli/main.py`, `src/web/app.py`.

## Feature & Defect Inventory
| # | Defect / Requirement | Description | Milestone | Source |
|---|----------------------|-------------|-----------|--------|
| 1 | Ruff E402 / F401 Lint Errors | 28 `E402` in `src/web/app.py` due to module-level `logger` placement; 2 `F401` in `test_wiki_vault_seeding_and_resilience.py`. | M1 (DONE) | Survey 1 |
| 2 | Mypy `LLMProviderPort.stream` Protocol | `async def stream` in Protocol causes coroutine-of-async-iterator mismatch; fix to `def stream(...) -> AsyncIterator[...]`. | M1 (DONE) | Survey 1 |
| 3 | Mypy Type Annotations & Attributes | Fix dict typing in `wiki/store.py`, `dynamic_loader.py`, `settings_service.py`, `agent_kernel.py`, `cli/main.py`, and `app.py`. | M1 (DONE) | Survey 1 |
| 4 | Telemetry Models Property Decorators | Reorder property/cached_property decorators in `src/domain/telemetry/models.py:29`. | M1 (DONE) | Survey 1 |
| 5 | `HandoffIsolationEngine` Method Call | `handoff_engine.py:128` calls non-existent `exec_kernel.execute_turn`; fix to `run_turn` (with fallback). | M2 | Survey 3 |
| 6 | `BuiltinAgentRegistry` Scoped Tool Registration | `registry.py:136` passes `ToolRegistration` instance to `register_tool`; fix to assign `scoped._tools[name] = tool`. | M2 (DONE in M1, verify in M2) | Survey 3 |
| 7 | `OpenAIProviderAdapter` Empty Choices Crash | `openai_adapter.py:187` raises `IndexError` on `{"choices": []}`; fix with defensive `data.get("choices") or [{}]`. | M2 | Survey 3 |
| 8 | `create_app` Wiki Path Binding | `app.py` `create_app` does not bind `app.state.wiki_service = WikiService(wiki_root=wiki_path)`; fix binding. | M2 | Survey 3 |
| 9 | Targeted Backend Unit Tests | Add unit tests for `HandoffIsolationEngine.execute_handoff`, `get_scoped_registry_for_agent`, and empty OpenAI choices. | M2 | Survey 3 |
| 10 | Missing `debounce` Helper in `app.js` | `app.js:1357` calls undefined `debounce`, throwing synchronous `ReferenceError` during `DOMContentLoaded` and breaking 41 buttons & 10 modals. | M3 | Survey 2 |
| 11 | Dangling DOM IDs & Null-Safety | `app.js:2633-2634` references non-existent `newNoteInboxPrioGroup` / `newNoteInboxPrioSelect`; add null-safe guards. | M3 | Survey 2 |
| 12 | UI Initialization Fault Tolerance | Wrap module initializers (Observability, Forge, Settings, Docs, Wiki) in modular try-catch blocks. | M3 | Survey 2 |
| 13 | Full Test Suite & Lint Verification | Verify `ruff check src/` (0 errors), `mypy src/ --ignore-missing-imports` (0 errors), `pytest tests/ -v` (100% pass). | M4 | Survey 1,3 |
| 14 | Comprehensive Audit Report | Generate `docs/audit/audit_report.md` accounting for all 64 buttons, 12 modals, 8 drawers, 17 tabs, backend fixes, and R1-R5 criteria. | M5 | ORIGINAL_REQUEST |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Static Analysis & Type Integrity | Fix all Ruff E402/F401 violations and Mypy typing errors across `src/` and `tests/`. | none | DONE |
| M2 | Backend Logic & Domain Integrity | Fix `handoff_engine.py`, `registry.py`, `openai_adapter.py`, `app.py` wiki binding, and add unit tests. | M1 | IN_PROGRESS |
| M3 | Frontend UI Wiring & Resilient Lifecycle | Add `debounce` in `app.js`, fix dangling DOM lookups, add null-safety, and verify all UI event bindings. | M2 | PLANNED |
| M4 | Test Suite & Static Analysis Validation | Execute full `pytest tests/ -v`, `ruff check src/`, `mypy src/ --ignore-missing-imports`, and verify 0 errors. | M3 | PLANNED |
| M5 | Comprehensive Audit Report & Forensic Verification | Author `docs/audit/audit_report.md` covering all UI components and backend resolutions; run Forensic Auditor. | M4 | PLANNED |

## Interface Contracts & Code Layout
### Code Layout & Write Ownership
- **Milestone 1**: `src/application/gateway/ports.py`, `src/domain/telemetry/models.py`, `src/domain/wiki/store.py`, `src/application/skills/dynamic_loader.py`, `src/application/settings/settings_service.py`, `src/application/kernel/agent_kernel.py`, `src/cli/main.py`, `src/web/app.py`, `tests/unit/web/test_wiki_vault_seeding_and_resilience.py`.
- **Milestone 2**: `src/application/orchestration/handoff_engine.py`, `src/infrastructure/agents/registry.py`, `src/infrastructure/gateway/openai_adapter.py`, `src/web/app.py` (wiki binding), `src/infrastructure/storage/sqlite_store.py` (commit consistency), `tests/unit/orchestration/test_handoff_engine.py`, `tests/unit/agents/test_registry_scoped.py`, `tests/unit/gateway/test_openai_empty_choices.py`.
- **Milestone 3**: `src/web/static/app.js`, `src/web/templates/index.html`.
- **Milestone 4**: `tests/**`.
- **Milestone 5**: `docs/audit/audit_report.md`.
