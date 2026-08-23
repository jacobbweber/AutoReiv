# Requirements Specification: Unified Settings Studio & Model Matrix

> **Spec Status**: Ready for Review  
> **Target Release**: Milestone 15 (v1.3.0)  
> **Primary Component**: `AutoReiv.Settings` & `AutoReiv.Web`  
> **Applicable ADRs**: `docs/adr/0016-unified-llm-provider-presets-and-dynamic-matrix-routing.md`  
> **Linked Work Card**: `.github/cards/CARD-015-unified-settings-studio-llm-providers-and-model-matrix.md`

---

## 1. Executive Summary & User Story
As an AutoReiv operator configuring AI providers and models,  
I want a unified Settings Studio where I can select from standard LLM provider presets (Ollama, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, vLLM), discover installed/available models with a single click, set active defaults, and configure purpose-based agent routing using discovered models,  
So that provider setup and model routing are intuitive, reliable, and free from configuration friction.

---

## 2. EARS Functional Requirements

### `[REQ-SET-001]` Standard LLM Provider Preset Registry & Defaults
- **Ubiquitous**: THE Settings Studio SHALL provide a single Provider Selector dropdown with built-in presets (Ollama, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Together, vLLM / Local), automatically populating standard default API Base URLs upon selection.

### `[REQ-SET-002]` Dynamic Model Discovery & Model Picker
- **Event-driven**: WHEN the user clicks "Refresh Models" or selects a configured provider, THE platform SHALL query the provider's model catalog and populate a Model Picker dropdown allowing selection and persistence of the active default model.

### `[REQ-SET-003]` Purpose-Based Model Matrix Harmonization
- **Ubiquitous**: THE platform SHALL display "Purpose-Based Model Routing" (with zero references to Hermes jargon) and populate each purpose category dropdown (*Default / General*, *Coding / Sysadmin*, *Documentation / Librarian*, *Fast / Routines*, *Auditing / Critic*) dynamically from all discovered models.

### `[REQ-SET-004]` Live Hardware & Memory Fit Validation
- **Event-driven**: WHEN models are discovered or RAM headroom is recalculated, THE platform SHALL compute parameter memory weights and display live fit classification badges (`PERFECT_FIT`, `TIGHT_FIT`, `EXCEEDS_MEMORY`) with estimated RAM/VRAM footprint in GiB.

### `[REQ-SET-005]` Consolidated Settings Studio SPA Interface
- **Ubiquitous**: THE Web UI SHALL consolidate LLM Providers, Active Default Model Selection, Purpose Routing Matrix, and Hardware Fit into an integrated, seamless settings layout.

### `[REQ-SET-006]` REST Settings & Model Discovery Endpoints
- **Event-driven**: WHEN a client requests `GET /api/settings/presets`, `GET /api/models/discover`, OR `POST /api/settings/providers`, THE backend SHALL return standard provider presets, query active provider models, and persist configuration state.
