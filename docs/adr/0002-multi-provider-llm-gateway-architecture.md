# ADR-0002: Multi-Provider LLM Gateway Architecture

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank

---

## 1. Context & Problem Statement

AutoReiv requires seamless access to diverse Large Language Models:
1. Local execution on hardware such as the user's Nimo Mini PC (128GB unified RAM running Ubuntu CLI with Ollama and Qwen models).
2. Remote cloud providers (OpenAI, OpenRouter, Anthropic-compatible endpoints) for heavier reasoning or fallback.
3. Real-time streaming token delivery for responsive UI chat and background routines.
4. Support for reasoning model outputs (`<think>` tags) without polluting final user responses.

We need a clean, decoupled architecture that isolates core agent business logic from vendor-specific HTTP APIs, schema variations, and network instability.

---

## 2. Decision Drivers

* **Clean Architecture (DIP / OCP)**: Domain and application logic must depend on abstract interfaces (`LLMProviderPort`), never on concrete third-party SDKs or raw HTTP endpoints.
* **Low Cognitive Friction & Local First**: Standard zero-config setup for local Ollama while supporting pluggable cloud APIs via environment variables.
* **Resilience**: Network drops or local server downtime should seamlessly trigger configured fallbacks without crashing active user sessions.
* **Zero Bloat**: Avoid massive third-party wrapper frameworks (e.g., heavy LangChain bundles) in favor of lightweight, standard `httpx` + `pydantic` adapters based on the `script-to-agent-labs` primitives.

---

## 3. Considered Options

* **Option 1**: Direct coupling to third-party orchestration frameworks (e.g. LangChain / LiteLLM proxy).
* **Option 2**: In-process LLM runtime (loading GGUF weights directly via `llama.cpp` bindings in Python).
* **Option 3 (Recommended)**: Ports & Adapters Architecture using standard `httpx` async clients for Ollama and OpenAI-compatible endpoints with a unified `MultiProviderGateway` router and fallback executor.

---

## 4. Decision Outcome

Chosen option: **Option 3 (Ports & Adapters Gateway)**, because:
- It maintains strict Clean Architecture boundaries and high testability with mock HTTP transports.
- It leverages the proven patterns from `script-to-agent-labs` (`00_atoms` to `06_the_reliability`).
- It offloads compute and model lifecycle to external runtimes (Ollama on the Nimo mini PC, cloud APIs) without inflating the AutoReiv application binary or introducing fragile C-extension compilation issues.

### Positive Consequences
* Zero third-party framework lock-in.
* 100% hermetic unit testing using `httpx.MockTransport` (no network calls or live LLMs required during automated CI/CD).
* Easy extensibility: adding a new provider requires only implementing `LLMProviderPort`.
* Reasoning tag separation is handled uniformly at the gateway layer.

### Negative Consequences / Trade-offs
* We maintain our own lightweight translation schemas for tool definitions and streaming deltas (mitigated by Pydantic models).
