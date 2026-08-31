# ADR-0016: Unified LLM Provider Presets and Dynamic Matrix Routing

## Status
Accepted

## Date
2026-08-23

## Context
Configuring LLM backends required manual endpoint entry and lacked unified provider presets. The purpose matrix referenced internal routing jargon and did not dynamically populate from discovered models. Users need a consolidated, multi-provider settings interface with standard provider presets, dynamic model discovery, default model assignment, and live hardware fit estimation.

## Decision Drivers
- **Standard Provider Presets**: Include industry-standard provider presets (Ollama, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Together, vLLM / Local) with pre-filled default URLs.
- **Dynamic Model Picker**: Refresh and populate model dropdowns across provider cards and purpose matrix directly from `list_models()`.
- **Purpose Matrix Harmonization**: Clean up naming to "Purpose-Based Model Routing", binding dropdown options directly to discovered models.
- **Validated Hardware Fit**: Live calculation of memory requirements (RAM/VRAM) across discovered models with clear fit indicators (`PERFECT_FIT`, `TIGHT_FIT`, `EXCEEDS_MEMORY`).

## Decision Outcome
Adopt `ProviderPresetRegistry`, dynamic model discovery synchronization, unified Settings Studio UI components, and clean purpose routing contracts.

## Consequences
- **Positive**: Zero-friction setup for popular LLM endpoints; cohesive UX connecting providers, discovered models, and purpose matrix.
- **Negative**: Requires maintaining standard provider base URL defaults and model listing schemas.
