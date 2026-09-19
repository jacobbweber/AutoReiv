# Design: Settings Model Context Overrides

Resolution order for a turn:

1. `purpose_matrix.model_context_windows[model_id]` (exact or provider-stripped)
2. `purpose_matrix.default_context_window`
3. Name-pattern table in `get_model_context_limit`

`AgentKernel._resolve_context_limit` reads SQLite `purpose_matrix`. Compaction uses 75% of that window. `CompletionRequest.num_ctx` is set to the full window; `OllamaProviderAdapter` sends it as `options.num_ctx`.

Name-table fallback for `qwen3.8` is 32768 (practical default). Hosts with large unified memory set 131072 or 262144 in Settings. Native qwen3.8 window is 262144.
