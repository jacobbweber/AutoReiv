# [CARD-062] Settings-Owned Model Context Window Overrides

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/settings-model-context-overrides/`
> **Labels**: `type:feature`, `area:kernel`, `area:settings`, `area:gateway`

---

## 1. Why / Intent
`get_model_context_limit` only special-cased `qwen2.5`, so live `qwen3.8:latest` was budgeted as 8192 (~6k after the 75% margin). Nimo reports a native 262144 window and has 128GB unified memory. A hardcoded 32k guess is still wrong for that host. Context must be an operator-owned Settings value (default + per model), with the name table as fallback only.

---

## 2. What to Build
- Expand `get_model_context_limit` for `qwen3.8` / `qwen35` and explicit size tags.
- Add `default_context_window` and `model_context_windows` to `ModelPurposeMatrix` and `POST /api/settings/matrix`.
- Settings Studio: default token input next to the default model; optional token input on each purpose slot.
- Kernel resolves overrides from SQLite and sets `CompletionRequest.num_ctx`; Ollama adapter sends `options.num_ctx`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-CTX-001]`: Name table no longer treats `qwen3.8:latest` as 8192.
- [x] `[REQ-CTX-002]`: Purpose matrix persists default and per-model context overrides.
- [x] `[REQ-CTX-003]`: Settings UI can set and save those overrides.
- [x] `[REQ-CTX-004]`: Compaction budget and Ollama `num_ctx` use the resolved window.
- [x] Automated tests green via `pytest` for the limiter and settings model.

---

## 4. Constraints & Honor Flags
- Name-table 32k is fallback only, not a hardware ceiling.
- Zero breaking changes to existing passing tests.
