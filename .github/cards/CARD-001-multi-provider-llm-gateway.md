# [CARD-001] Multi-Provider LLM Gateway & Stream Demuxer

> **Status**: Completed (Merged to `qa`)  
> **Milestone**: Milestone 1 (v0.1.0)  
> **Primary Component**: `AutoReiv.Gateway`  
> **Spec Reference**: `docs/specs/multi-provider-llm-gateway/`  
> **ADR Reference**: [`docs/adr/0002-multi-provider-llm-gateway-and-reasoning-stream-demuxer.md`](file:///d:/Projects/Active/AutoReiv/docs/adr/0002-multi-provider-llm-gateway-and-reasoning-stream-demuxer.md)  
> **Requirements**: `[REQ-GW-001]` to `[REQ-GW-006]`

---

## 1. Why / Intent
AutoReiv is a local-first autonomous agent platform. It must seamlessly interface with local LLM providers (e.g. Ollama running on a Nimo Mini PC 2L with unified memory) while maintaining transparent failover and routing to OpenAI-compatible cloud endpoints without coupling core agent logic to specific provider SDKs. Deep reasoning tokens (`<think>` blocks from models like DeepSeek-R1 / Qwen-2.5) must be cleanly separated from user-facing answer text in real time.

---

## 2. What Was Built
- **Ports & Adapters Architecture**: `LLMProviderPort` interface implemented by `OllamaProviderAdapter` and `OpenAIProviderAdapter`.
- **`MultiProviderGateway` Service**: Dynamic provider routing (`provider/model` syntax), automatic fallback chains, and timeout handling.
- **Streaming Demuxer (`ReasoningDemuxer`)**: State-machine parser for real-time SSE chunk splitting (`<think>` reasoning vs content tokens).
- **Domain Models & Errors**: Typed dataclasses for `CompletionRequest`, `CompletionResponse`, `StreamChunk`, and domain exceptions.

---

## 3. Acceptance Criteria & Automated Proof
- [x] `[REQ-GW-001]`: Ollama HTTP streaming and tool calling integration verified.
- [x] `[REQ-GW-002]`: OpenAI-compatible HTTP streaming and structured error mappings verified.
- [x] `[REQ-GW-003]`: Multi-provider routing and default provider fallback chains verified.
- [x] `[REQ-GW-004]`: `<think>` tag token stream demuxing verified with unit tests.
- [x] `[REQ-GW-005]`: Automated unit test suite passing (`tests/unit/gateway/`).
- [x] `[REQ-GW-006]`: 100% RTM traceability compliance.
