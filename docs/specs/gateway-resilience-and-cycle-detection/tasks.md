# Task Breakdown: Gateway Resilience Hardening & Streaming Cycle Detection

> **Spec Status**: Implemented  
> **Target Release**: Milestone 12 (v0.12.0)  
> **Card Reference**: [CARD-043](file:///.github/cards/CARD-043-gateway-resilience-hardening-and-streaming-cycle-detection.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/gateway-resilience-and-cycle-detection/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/gateway-resilience-and-cycle-detection/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Gateway Retry & Connection Pool Resilience
- [x] **Task 1.1**: Enhance `src/application/gateway/gateway_service.py` with `calculate_backoff` (full-jitter exponential backoff) and configurable retry parameters (`[REQ-RESIL-001]`).
- [x] **Task 1.2**: Update `src/infrastructure/gateway/openai_adapter.py` and `ollama_adapter.py` with explicit keep-alive pool limits and `async def close()` (`[REQ-RESIL-002]`).

### Slice 2: Dual-Mode Cycle & Loop Detection
- [x] **Task 2.1**: Upgrade `src/application/kernel/cycle_detector.py` to support `record_and_check_text` for streaming text loop detection (`[REQ-RESIL-003]`).
- [x] **Task 2.2**: Integrate cycle check alerts into `src/application/kernel/agent_kernel.py` (`[REQ-RESIL-003]`).

### Slice 3: Verification, Pre-Flight & Milestone 12 Gate Closure
- [x] **Task 3.1**: Author unit and integration tests in `tests/unit/gateway/test_resilience.py` (`[REQ-RESIL-004]`).
- [x] **Task 3.2**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-RESIL-004]`).
- [x] **Task 3.3**: Author ADR-0043 and sync `docs/rtm.json` with `[REQ-RESIL-001]` through `[REQ-RESIL-004]`.
- [x] **Task 3.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

