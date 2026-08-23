# [CARD-015] Unified Settings Studio LLM Providers and Model Matrix

> **Status**: Ready
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/unified-settings-studio/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Consolidate LLM provider configuration with provider preset dropdowns, dynamic model discovery, default model assignment, purpose-based matrix cleanup, and hardware fit validation

---

## 2. What to Build
Provider presets (Ollama, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, vLLM), live model picker, unified purpose matrix, and validated hardware fit

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
