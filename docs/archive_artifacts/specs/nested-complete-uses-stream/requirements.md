# Nested Complete Uses Stream

## REQ-ORCH-026
`OllamaProviderAdapter.complete` must POST `/api/chat` with `stream=true` and assemble `CompletionResponse` from `StreamChunk` content and tool_calls. Nested `run_turn` (Coding handoff) and parent Chat share this shape.

## REQ-ORCH-027
Timeout, connect, and 404 still raise `ProviderUnavailableError` / `ModelNotFoundError`. Token usage is taken from the done chunk (`prompt_eval_count` / `eval_count`) when present.
