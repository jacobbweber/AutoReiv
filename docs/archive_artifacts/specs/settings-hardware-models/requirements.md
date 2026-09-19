# Requirements Specification: Settings Studio & Hardware Fit Calculator

> **Spec Status**: Implemented  
> **Target Release**: Milestone 5 (v0.5.0)  
> **Primary Component**: `AutoReiv.Settings`  
> **Applicable ADRs**: `docs/adr/0006-live-model-discovery-hardware-fit-recommendations-and-purpose-routing.md`

---

## 1. Executive Summary & Intent

Milestone 5 implements the **Settings Studio**, providing dynamic provider configuration, auto-populated model discovery from local Ollama and cloud OpenAI APIs, Purpose-Based Model Routing (Reasoning, Task Execution, Fast, Vision, Auxiliary), hardware capacity estimation (tailored for high-memory mini PCs like the 128GB Nimo PC), and dynamic agent tone/tool customization.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-SETTINGS-001]: Live Provider Model Discovery
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator requests a model list refresh THE SYSTEM SHALL query connected provider endpoints (Ollama /api/tags, OpenAI /v1/models) and return unified model descriptors (model ID, family, parameter size, quantization).`
- **Acceptance Criteria**:
  - [ ] Given a live or mock Ollama provider, when `list_models()` is called, then it returns available local models parsed into `ModelDescriptor` objects.
  - [ ] Given a live or mock OpenAI provider, when `list_models()` is called, then it returns available models.

### [REQ-SETTINGS-002]: Purpose-Based Model Routing Matrix
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL maintain model bindings for specific operational purposes (GENERAL, REASONING, TASK_EXECUTION, VISION, AUXILIARY, FAST) and resolve model targets dynamically.`
- **Acceptance Criteria**:
  - [ ] Given a configured purpose matrix where `REASONING -> "ollama/qwen2.5:32b"`, when querying the model for reasoning, then it resolves to `"ollama/qwen2.5:32b"`.
  - [ ] Given an unassigned purpose, when queried, then it falls back gracefully to the platform default model.

### [REQ-SETTINGS-003]: Host Hardware Capacity Auto-Detection
- **Type**: Event-Driven
- **EARS Statement**: `WHEN assessing hardware capacity THE SYSTEM SHALL auto-detect physical RAM, logical cores, and platform architecture, allowing operator manual overrides (e.g. 128GB unified memory).`
- **Acceptance Criteria**:
  - [ ] Given `get_hardware_specs()`, when invoked without overrides, then it returns the detected host RAM and CPU core count.
  - [ ] Given explicit hardware overrides (e.g. `total_ram_gb=128.0`), when invoked, then recommendations use the overridden capacity.

### [REQ-SETTINGS-004]: Model Quantization & RAM Fit Calculator
- **Type**: Ubiquitous
- **EARS Statement**: `WHEN evaluating an LLM architecture, parameter size (e.g. 3B, 7B, 14B, 32B, 70B), and quantization (Q4_K_M, Q8_0, FP16) THE SYSTEM SHALL calculate memory footprint and classify fit status (OPTIMAL, RUNNABLE, OFFLOADED, INSUFFICIENT_MEMORY).`
- **Acceptance Criteria**:
  - [ ] Given a 128GB host and a 70B model at Q4_K_M (~43GB RAM required), when calculated, then fit status is `OPTIMAL`.
  - [ ] Given a 16GB host and a 70B model at FP16 (~145GB RAM required), when calculated, then fit status is `INSUFFICIENT_MEMORY`.

### [REQ-SETTINGS-005]: Dynamic Agent Profile & Tone Customization
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator updates an agent's tone, system prompt, model override, or allowed tools THE SYSTEM SHALL persist the customized manifest in SQLite and override default built-in profiles.`
- **Acceptance Criteria**:
  - [ ] Given an agent update saving `tone=AgentTone.SOCRATIC` in SQLite, when `get_effective_profile("general-assistant")` is queried, then it returns the updated profile with Socratic tone.

### [REQ-SETTINGS-006]: Unified Settings Repository & Key-Value Persistence
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist platform settings, provider configs, and purpose matrices in SQLite.`
- **Acceptance Criteria**:
  - [ ] Given settings updates, when persisted to SQLite, then they survive application restarts and are queried deterministically.

---

## 3. Non-Functional & Boundary Constraints

- **Cross-Platform Resilience**: Model discovery handles network timeouts and provider unreachability gracefully without throwing unhandled exceptions.
- **Hermetic Testing**: All tests execute against mock HTTP provider responses and in-memory SQLite tables.

---

## 4. Out of Scope

- Live React/Vue web UI controls (Milestone 7).
