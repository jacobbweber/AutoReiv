# Requirements Specification: Multi Provider Gateway

> **Spec Status**: Implemented  
> **Target Release**: Milestone 1 (v0.1.0)  
> **Primary Component**: `AutoReiv.Gateway`  
> **Applicable ADRs**: `docs/adr/0002-multi-provider-llm-gateway-architecture.md`

---

## 1. Executive Summary & Intent

The Multi-Provider LLM Gateway serves as AutoReiv's unified translation and dispatch layer for Large Language Models. It abstracts differences between local backends (e.g., Ollama running on LAN mini PCs / Ubuntu) and remote cloud APIs (OpenAI, OpenRouter, Anthropic-compatible proxies), providing streaming token delivery, standardized tool-calling schemas, automatic fallback on failures, and reasoning token demuxing (`<think>` tags).

---

## 2. User Stories & EARS Functional Requirements

### [REQ-GW-001]: Unified Chat Message & Model Protocol
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL represent all conversational interactions using a normalized schema supporting roles ('system', 'user', 'assistant', 'tool'), text content, tool calls, and model metadata.`
- **Acceptance Criteria**:
  - [ ] Given a list of messages with system, user, assistant, and tool turns, when normalized into domain models, then all message roles and contents are validated strictly.
  - [ ] Given a tool definition with JSON schema parameters, when attached to a completion request, then it conforms to the unified tool specification.
  - [ ] Given an invalid message role or missing required content, when parsed, then the system raises a `GatewayValidationError`.

### [REQ-GW-002]: Provider Port & Registry
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide an abstract LLM Provider Port interface and dynamic provider registry allowing runtime registration and lookup of LLM backends.`
- **Acceptance Criteria**:
  - [ ] Given a configured provider name (e.g. `'ollama-local'`, `'openai-cloud'`), when looked up in the registry, then the appropriate provider adapter is returned.
  - [ ] Given an unknown provider ID, when requested, then the registry raises `ProviderNotFoundError`.

### [REQ-GW-003]: Local Ollama Provider Adapter
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a completion or streaming request targets an Ollama backend THE SYSTEM SHALL format and dispatch the request to the configured Ollama HTTP endpoint (/api/chat) and return normalized token chunks or responses.`
- **Acceptance Criteria**:
  - [ ] Given a target Ollama base URL (e.g. `http://192.168.1.50:11434` or `http://127.0.0.1:11434`) and model `qwen2.5:7b`, when `complete()` is called, then it yields a normalized `CompletionResponse`.
  - [ ] Given a streaming request to Ollama, when `stream()` is called, then it yields an async iterator of `StreamChunk` objects containing incremental text and tool call deltas.
  - [ ] Given an unreachable Ollama host, when queried, then it raises `ProviderUnavailableError`.

### [REQ-GW-004]: OpenAI-Compatible Provider Adapter
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a request targets an OpenAI-compatible API THE SYSTEM SHALL dispatch HTTP requests with Authorization Bearer headers and parse Server-Sent Events (SSE) data streams into normalized chunks.`
- **Acceptance Criteria**:
  - [ ] Given an API key and base URL, when sending non-streaming requests, then it parses choices, finish reasons, and tool calls into `CompletionResponse`.
  - [ ] Given an SSE streaming response (`data: {...}`), when streaming tokens, then it emits `StreamChunk` items ending with `is_finished=True`.
  - [ ] Given an HTTP 401 response from the provider, when received, then it raises `AuthenticationError`.

### [REQ-GW-005]: Resilient Failover & Fallback
- **Type**: Complex / Error-Handling
- **EARS Statement**: `WHEN a primary provider request encounters a network failure or 5xx server error THE SYSTEM SHALL sequentially attempt execution against configured fallback provider/model candidates.`
- **Acceptance Criteria**:
  - [ ] Given a primary model `'ollama/qwen3.8'` and fallback `'openai/gpt-4o-mini'`, when Ollama fails with a connection error, then the gateway automatically executes the query on the fallback provider.
  - [ ] Given all fallback providers fail, when exhausted, then the gateway raises a consolidated `AllProvidersFailedError` with individual error details.

### [REQ-GW-006]: Reasoning Tag Demuxer
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an LLM token stream contains reasoning tags (<think>...</think>) THE SYSTEM SHALL demux the stream into separate 'reasoning_content' and 'content' fields.`
- **Acceptance Criteria**:
  - [ ] Given a stream emitting `<think>Let's analyze this.</think>Here is the answer.`, when demuxed, then the reasoning chunk contains `"Let's analyze this."` and the user-facing chunk contains `"Here is the answer."`.
  - [ ] Given non-reasoning standard output, when processed, then text passes through directly with empty reasoning content.

---

## 3. Non-Functional & Boundary Constraints

- **Async-First**: All network calls and streaming generators use `asyncio` and `httpx.AsyncClient` without blocking the main event loop.
- **Hermetic Testing**: Unit tests use mock transport (`httpx.MockTransport`) with zero outbound network calls.
- **Latency & Streaming**: Stream chunks are yielded immediately upon arrival from downstream sockets with sub-5ms internal buffering overhead.
- **Clean Architecture / DIP**: Domain entities depend on no external HTTP or IO libraries.

---

## 4. Out of Scope

- User authentication / JWT tokens (deferred to Milestone 5 Front-Door API).
- Agent execution loop and tool calling recursion (handled in Milestone 2 Agent Kernel).
- Direct fine-tuning or model weight loading in-process (delegated to external Ollama / vLLM runtime).
