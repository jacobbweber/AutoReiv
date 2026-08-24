# Requirements Specification: Gateway Resilience Hardening & Streaming Cycle Detection

> **Spec Status**: Approved  
> **Target Release**: Milestone 12 (v0.12.0)  
> **Card Reference**: [CARD-043](file:///.github/cards/CARD-043-gateway-resilience-hardening-and-streaming-cycle-detection.md)  

> **Primary Component**: AutoReiv Gateway & Agent Kernel (`src/application/gateway/gateway_service.py`, `src/infrastructure/gateway/`, `src/application/kernel/cycle_detector.py`)

---

## 1. Executive Summary & Intent

**CARD-043** hardens the gateway and agent execution runtime against transient network errors, connection pool exhaustion, and model generation repetition cycles, completing **Milestone 12**.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-RESIL-001] Exponential Backoff with Decorrelated Jitter
- **EARS Pattern**: Ubiquitous
- **Requirement**: The `MultiProviderGateway` **shall** implement `calculate_backoff(attempt, initial_delay, backoff_factor, max_delay)` computing bounded full-jitter exponential backoff ($d \in [0, \min(M, D_0 \times B^i)]$) for transient 5xx, rate limits, and network errors.

### [REQ-RESIL-002] Connection Pool Limits & Graceful Lifecycle Management
- **EARS Pattern**: Ubiquitous
- **Requirement**: The `OpenAIProviderAdapter` and `OllamaAdapter` **shall** configure explicit connection limits (`max_keepalive_connections=20`, `max_connections=50`, `keepalive_expiry=30.0`) and provide an `async def close()` method to prevent socket leakage.

### [REQ-RESIL-003] Dual-Mode Agent Cycle & Content Loop Detector
- **EARS Pattern**: Event-Driven
- **Requirement**: When reasoning or streaming tokens are produced, the `CycleDetector` **shall** detect repeated tool call signatures via `record_and_check` and repeated text n-grams via `record_and_check_text`, enabling `AgentKernel` to abort infinite loops safely.

### [REQ-RESIL-004] Comprehensive Gateway Resilience Unit Test Suite
- **EARS Pattern**: State-Driven
- **Requirement**: When running `pytest`, the test runner **shall** verify backoff jitter distributions, adapter connection pool configuration, tool/text cycle detection, and fallback routing with 100% passing tests.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `calculate_backoff` produces values bounded between $0$ and `max_delay`.
- [ ] `AC-2`: Adapters instantiate with `httpx.Limits` and support `close()`.
- [ ] `AC-3`: `CycleDetector` identifies repeating phrases and tool signatures.
- [ ] `AC-4`: `npm run preflight` passes all 6 quality gates cleanly.
