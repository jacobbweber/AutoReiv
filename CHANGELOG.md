# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Multi-Provider LLM Gateway (`AutoReiv.Gateway`) with unified message schema (`ChatMessage`, `Role`, `ToolCall`).
- Abstract `LLMProviderPort` protocol and dynamic provider registry.
- `OllamaProviderAdapter` for local/LAN Ollama execution with streaming and tool calling.
- `OpenAIProviderAdapter` for OpenAI-compatible cloud/local endpoints with SSE streaming.
- `MultiProviderGateway` orchestrator with multi-model fallback execution chains.
- `ReasoningDemuxer` for splitting `<think>...</think>` tokens in real-time streams.
- `GatewayProviderFactory` for zero-boilerplate initialization from environment variables.
- 30 hermetic unit tests with mock HTTP transports and zero outbound network calls.
- Initialized AutoReiv project steering (`product.md`, `tech.md`) and RTM traceability.
