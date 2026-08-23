# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Settings Studio Engine (`AutoReiv.Settings`): Dynamic live model discovery, purpose matrix routing, and hardware fit estimation.
- Live model discovery on `OllamaProviderAdapter` (`/api/tags`) and `OpenAIProviderAdapter` (`/v1/models`) with parameter size and quant level extraction.
- Hermes-style Purpose-Based Model Routing (`ModelPurposeMatrix`) for `GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, and `FAST` operational roles.
- `HardwareFitCalculator` predicting model RAM footprint (weight bits + KV cache headroom) and classifying host fit (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`) with custom specs overrides (e.g. 128GB Nimo PC).
- `SettingsService` for unified settings key-value management and runtime agent persona/tone/prompt customizations (`AgentCustomization`).
- SQLite persistence tables (`settings` and `agent_overrides`) for zero-loss configuration storage across application restarts.
- Autonomous Routine Engine & Background Scheduler (`AutoReiv.Routines`).
- Declarative `Routine` and `RoutineRun` models with interval and cron schedule configurations.
- SQLite persistence for routine configurations and chronological execution run histories (`routines` and `routine_runs` tables).
- `ScheduleMatcher` for deterministic interval and cron due time calculations.
- `RoutineExecutor` for isolated autonomous session execution via `AgentKernel` and automatic telemetry span recording.
- `RoutineScheduler` with non-blocking async tick loop and manual out-of-schedule trigger API.
- 4 Day-1 default routine manifests: Morning Briefing, Daily System Info, Nightly Note Hygiene, and Hourly SRE Pulse.
- 4 Built-In Agent Manifests (`AutoReiv.Agents`): General Assistant, Linux Sysadmin, Librarian, and System Agent.
- `TaskTrackerSkill` with SQLite-backed task CRUD (`create_task`, `list_tasks`, `update_task_status`, `delete_task`).
- `SysadminSkill` with cross-platform host metrics (`get_system_info`) and asynchronous timeout-protected command execution (`cli_exec`).
- `LibrarianSkill` with YAML frontmatter parser and path-jailed PARA-Wiki note creator (`wiki_note_create`, `wiki_note_read`, `wiki_note_list`).
- `SystemAgentSkill` providing platform health diagnostics, database latency testing, and token usage summaries.
- `BuiltinAgentRegistry` for one-line ecosystem bootstrapping and automatic scoped tool binding.
- Agent Kernel & ReAct execution engine (`AutoReiv.Kernel`) supporting multi-turn tool loops, cycle detection, and max turn budgeting.
- Declarative `AgentProfile` manifest with configurable `AgentTone` prompt directive formatting.
- `ScopedToolRegistry` with strict Role-Based Access Control (RBAC) tool execution permissions.
- `SQLiteStateStore` with WAL mode (`AutoReiv.Memory`) for chronological conversation checkpointer and session management.
- `TelemetryCollector` and `TelemetrySpan` tracking per-agent token usage, tool reliability/error metrics, and global platform KPIs.
- Real-time streaming `KernelEvent` generator for tokens, tool execution starts, tool outputs, and turn completions.
- Multi-Provider LLM Gateway (`AutoReiv.Gateway`) with unified message schema (`ChatMessage`, `Role`, `ToolCall`).
- Abstract `LLMProviderPort` protocol and dynamic provider registry.
- `OllamaProviderAdapter` for local/LAN Ollama execution with streaming and tool calling.
- `OpenAIProviderAdapter` for OpenAI-compatible cloud/local endpoints with SSE streaming.
- `MultiProviderGateway` orchestrator with multi-model fallback execution chains.
- `ReasoningDemuxer` for splitting `<think>...</think>` tokens in real-time streams.
- `GatewayProviderFactory` for zero-boilerplate initialization from environment variables.
- 55 hermetic unit tests with mock HTTP transports and zero outbound network calls.
