# ADR-0043: Gateway Resilience Hardening & Streaming Cycle Detection

## Context
AutoReiv routes agent tool-calling turns across local (Ollama) and cloud (OpenAI, Anthropic, Gemini) LLM providers. Production workflows require resilience against transient socket drops, 5xx server errors, connection pool starvation, and infinite generation/tool loops.

## Decision
1. **Decorrelated Full Jitter**:
   - Implemented `MultiProviderGateway.calculate_backoff(attempt, initial_delay, backoff_factor, max_delay)` computing bounded random backoff delays to prevent synchronized retry storms.
2. **HTTP Connection Pool Management**:
   - Standardized `httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0)` across `OpenAIProviderAdapter` and `OllamaProviderAdapter`.
   - Added explicit `async def close(self)` lifecycle teardown.
3. **Dual-Mode Cycle & Loop Detection**:
   - Upgraded `CycleDetector` to analyze both consecutive tool-call execution signatures (`record_and_check`) and suffix word n-grams/exact substrings (`record_and_check_text`).
   - Integrated cycle break assertions directly into `AgentKernel` synchronous and streaming turn loops.

## Status
Accepted

## Consequences
- **Positive**: High tolerance against transient gateway network errors, zero socket leakage under sustained concurrency, and safe auto-termination for looping LLMs.
- **Negative**: Adds light runtime regex/n-gram inspection on streaming chunk accumulation.
