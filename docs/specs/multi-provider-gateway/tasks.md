# Implementation Tasks: Multi Provider Gateway

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-GW-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Domain Entities & Gateway Port Definitions
- [x] **Task 1.1** `[REQ-GW-001]`: [RED] Write failing unit tests in `tests/unit/gateway/test_domain_models.py` for `ChatMessage`, `Role`, `ToolCall`, `CompletionRequest`, `StreamChunk`, and `CompletionResponse`.
- [x] **Task 1.2** `[REQ-GW-001]`: [GREEN] Implement domain models in `src/domain/gateway/models.py` and exceptions in `src/domain/gateway/errors.py`.
- [x] **Task 1.3** `[REQ-GW-002]`: [GREEN] Define `LLMProviderPort` protocol in `src/application/gateway/ports.py`.

### Slice 2: Reasoning Tag Demuxer
- [x] **Task 2.1** `[REQ-GW-006]`: [RED] Write failing unit tests in `tests/unit/gateway/test_reasoning_demuxer.py` for streaming `<think>` and non-reasoning token streams.
- [x] **Task 2.2** `[REQ-GW-006]`: [GREEN] Implement `ReasoningDemuxer` state machine in `src/application/gateway/demuxer.py`.
- [x] **Task 2.3** `[REQ-GW-006]`: [REFACTOR] Ensure clean handling of partial split tokens (e.g. `<thi` + `nk>`).

### Slice 3: Ollama Provider Adapter
- [x] **Task 3.1** `[REQ-GW-003]`: [RED] Write failing unit tests with mock transport in `tests/unit/gateway/test_ollama_adapter.py` for Ollama completion and streaming.
- [x] **Task 3.2** `[REQ-GW-003]`: [GREEN] Implement `OllamaProviderAdapter` in `src/infrastructure/gateway/ollama_adapter.py`.
- [x] **Task 3.3** `[REQ-GW-003]`: [REFACTOR] Standardize error mapping for connection refusals and missing models.

### Slice 4: OpenAI-Compatible Provider Adapter
- [x] **Task 4.1** `[REQ-GW-004]`: [RED] Write failing unit tests with mock transport in `tests/unit/gateway/test_openai_adapter.py` for OpenAI SSE streaming and tool calling.
- [x] **Task 4.2** `[REQ-GW-004]`: [GREEN] Implement `OpenAIProviderAdapter` in `src/infrastructure/gateway/openai_adapter.py`.
- [x] **Task 4.3** `[REQ-GW-004]`: [REFACTOR] Handle 401 authentication and rate limit status codes cleanly.

### Slice 5: Gateway Orchestrator & Multi-Model Fallback
- [x] **Task 5.1** `[REQ-GW-002]`, `[REQ-GW-005]`: [RED] Write failing unit tests in `tests/unit/gateway/test_gateway_service.py` for provider registry, model routing, and fallback chains.
- [x] **Task 5.2** `[REQ-GW-002]`, `[REQ-GW-005]`: [GREEN] Implement `MultiProviderGateway` orchestrator in `src/application/gateway/gateway_service.py`.
- [x] **Task 5.3** `[REQ-GW-002]`: [GREEN] Implement `GatewayProviderFactory` in `src/infrastructure/gateway/factory.py` loading configurations from environment variables.

### Slice 6: Verification, Traceability, & QA Gate
- [x] **Task 6.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 6.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 6.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
