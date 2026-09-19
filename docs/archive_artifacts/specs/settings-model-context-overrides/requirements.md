# Requirements: Settings Model Context Overrides

- `[REQ-CTX-001]`: `get_model_context_limit` recognizes `qwen3.8` / `qwen35` and explicit size tags (`65k`, `256k`, `262k`) instead of falling through to 8192.
- `[REQ-CTX-002]`: `ModelPurposeMatrix` stores `default_context_window` and `model_context_windows`.
- `[REQ-CTX-003]`: Settings Studio exposes default and per-purpose context token inputs; Save Matrix persists them via `POST /api/settings/matrix`.
- `[REQ-CTX-004]`: Agent kernel uses Settings overrides first, then the name table; Ollama requests send the same value as `num_ctx`.
