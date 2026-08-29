# [CARD-005] Settings Studio & Live Model Discovery

> **Status**: Done  
> **Milestone**: Milestone 5 (v0.5.0)  
> **Primary Component**: `AutoReiv.Settings`  
> **Spec Reference**: `docs/specs/settings-studio-and-model-discovery/`  
> **ADR Reference**: [`docs/adr/0006-settings-studio-purpose-matrix-and-hardware-fit-estimation.md`](file:///d:/Projects/Active/AutoReiv/docs/adr/0006-settings-studio-purpose-matrix-and-hardware-fit-estimation.md)  
> **Requirements**: `[REQ-SETTINGS-001]` to `[REQ-SETTINGS-006]`

---

## 1. Why / Intent
Users must be able to configure LLM provider API URLs and tokens directly through the UI, discover active models dynamically, route models by operational purpose (Hermes-style purpose matrix: General, Reasoning, Task, Vision, Fast, Aux), and accurately estimate whether models fit within host RAM (specifically optimized for a 128GB Unified Memory Nimo Mini PC).

---

## 2. What Was Built
- **Live Model Discovery**: Query active tags and parameter sizes from Ollama (`/api/tags`) and OpenAI (`/v1/models`).
- **Purpose Routing Matrix (`ModelPurposeMatrix`)**: Role-based model mappings (`GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, `FAST`).
- **Hardware RAM Fit Calculator (`HardwareFitCalculator`)**: Memory footprint prediction (parameter weight bits + KV cache headroom) classifying host fit (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`) with custom RAM overrides (e.g. 128GB Mini PC).
- **Settings Service & Key-Value Storage**: SQLite persistence for provider credentials, matrix routing, and agent persona overrides.

---

## 3. Acceptance Criteria & Automated Proof
- [x] `[REQ-SETTINGS-001]`: Live provider model discovery verified.
- [x] `[REQ-SETTINGS-002]`: Hermes-style purpose routing matrix resolution verified.
- [x] `[REQ-SETTINGS-003]`: Host hardware detection and 128GB RAM fit estimation verified.
- [x] `[REQ-SETTINGS-004]`: Runtime agent persona, tone, and tool customization verified.
- [x] `[REQ-SETTINGS-005]`: Automated unit test suite passing (`tests/unit/settings/`).
- [x] `[REQ-SETTINGS-006]`: 100% RTM traceability compliance.
