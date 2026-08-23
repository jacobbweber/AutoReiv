# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Reflexive Self-Verification Loops & SRE Health Auditing (`AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Agents`):
  - Deterministic `VerificationSkill` (`src/application/skills/verification_skill.py`) exposing ground-truth assertion tools: `verify_telemetry_consistency`, `assert_json_schema`, and `validate_metric_bounds`.
  - Iterative `ReflexionLoopEngine` (`src/application/kernel/reflexion_engine.py`) catching verification discrepancies, feeding structured critique notes back to the model, and orchestrating multi-turn autonomous refinement loops (up to 3 attempts).
  - Kernel verified execution methods `kernel.run_verified_turn` and integration into `AgentKernel`.
  - Built-in `auditor-critic` agent profile (`src/domain/agents/profiles.py`) specialized in zero-shot adversarial reviews, risk scoring (1-10), and assumption validation.
  - REST endpoints `POST /api/chat/verified` and `POST /api/agents/audit` for verified execution and external audit pipelines.
- Model Context Protocol (MCP) Client Adapter & Dynamic Skill Loader (`AutoReiv.MCP` & `AutoReiv.Skills`):
  - Standard JSON-RPC 2.0 `MCPClientAdapter` (`src/infrastructure/mcp/client_adapter.py`) managing stdio subprocess transports, tool discovery (`tools/list`), and execution (`tools/call`).
  - Dynamic `SKILL.md` parser `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) discovering YAML frontmatter and JSON tool manifests.
  - `mount_mcp_tool` integration in `ScopedToolRegistry` dynamically binding MCP tools with RBAC enforcement.
  - SQLite persistent MCP server registry and REST routes `GET /api/mcp/servers` and `POST /api/mcp/servers`.
- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation (`AutoReiv.Orchestration`):
  - Standardized 5-Key `HandoffEnvelope` domain model (`src/domain/orchestration/models.py`) transferring intent and hydrated context across agent boundaries.
  - `SupervisorOrchestrator` (`src/application/kernel/supervisor_orchestrator.py`) managing specialist agent dispatch, execution, and response synthesis.
  - `DelegateSubtaskSkill` (`src/application/skills/delegate_skill.py`) exposing `delegate_task` tool to allow coordinator agents to route sub-problems.
  - `handoff` telemetry spans linking parent session, sender, recipient, and correlation IDs.
  - REST endpoint `POST /api/agents/delegate` for direct external invocation of specialized workflows.
- Ephemeral Subprocess Sandbox & HITL Approvals (`AutoReiv.Safety` & `AutoReiv.Kernel`):
  - `DangerousCommandFilter` (`src/application/skills/command_filter.py`) statically rejecting destructive commands (`rm -rf /`, `dd`, `mkfs`, `format c:`, raw DB drop queries).
  - `SandboxedSubprocessWorker` (`src/application/skills/sandbox_worker.py`) executing CLI commands and Python scripts within isolated temporary directories with strict timeouts and cleanup.
  - `is_high_risk` tool metadata and `HITLApprovalEngine` (`src/application/kernel/hitl_engine.py`) parking execution awaiting human operator decisions.
  - SQLite `pending_approvals` table and REST endpoints (`GET /api/approvals/pending`, `POST /api/approvals/{id}/decision`) to approve or reject parked tool calls.
  - Real-time streaming cancellation endpoint (`POST /api/chat/stream/{session_id}/abort`) to abort in-flight agent reasoning loops.
- Context Window Compaction & Episodic Memory (`AutoReiv.Memory` & `AutoReiv.Kernel`):
  - `ContextCompactor` (`src/application/kernel/context_compactor.py`) implementing sliding-window message preservation, intermediate turn summarization, and large tool output pruning (>8000 chars) to prevent context window overflow.
  - `episodic_facts` SQLite table and `EpisodicMemorySkill` (`src/application/skills/memory_skill.py`) storing discrete cross-session facts (user preferences, environment settings).
  - Gateway transient error resilience with localized exponential backoff and randomized jitter in `MultiProviderGateway._execute_with_retry`.
  - HTTP persistent client connection pooling (`httpx.Limits(max_keepalive_connections=20)`) in `OllamaProviderAdapter` and `OpenAIProviderAdapter`.
  - `CycleDetector` (`src/application/kernel/cycle_detector.py`) enforcing repetition trap detection across both synchronous `run_turn` and real-time `stream_turn`.
- Multi-OS Packaging & Bare-Metal / Docker Deployment (`AutoReiv.Deploy`): Unified CLI tool (`autoreiv`), background routine engine server lifespan, Ubuntu systemd daemon, Windows service scripts, and Docker Compose with persistent volume mounts.
- Unified CLI entry point (`src/cli/main.py`) with commands:
  - `autoreiv serve`: Launches FastAPI web server and routine tick engine.
  - `autoreiv status`: Reports host CPU/RAM specs, database connectivity, and registered agents.
  - `autoreiv chat`: Interactive terminal chat loop with live token streaming.
  - `autoreiv routine [list|run]`: Direct terminal management and one-shot trigger of background routines.
- FastAPI `lifespan` context manager running `RoutineScheduler` background task concurrently with web request handling.
- Ubuntu / Debian `systemd` daemon unit file (`deploy/systemd/autoreiv.service`) and automated installer (`deploy/systemd/install_systemd.sh`) optimized for Mini PC bare-metal deployment.
- Windows PowerShell runner (`deploy/windows/run_autoreiv.ps1`), batch runner (`run_autoreiv.bat`), and service registration script (`install_windows_service.ps1`).
- Multi-stage production `Dockerfile` with non-root security user, health check, and `docker-compose.yml` with host volume mounts for persistent database (`./data/autoreiv.db`) and wiki documents (`./data/wiki`).
- Environment variable configuration template (`.env.example`) documenting `OLLAMA_HOST`, `OLLAMA_MODEL`, `OPENAI_API_KEY`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH`, and `PORT`.
- Responsive Web & Mobile Front-Door with Wiki Export (`AutoReiv.Web`): Complete zero-build Single-Page Application (SPA) with real-time SSE streaming, collapsible `<think>` tags, and one-click PARA-Wiki markdown export.
- FastAPI application backend (`src/web/app.py`) providing unified REST and SSE endpoints for agents, sessions, chat streaming, wiki note export, settings matrix, KPI dashboard metrics, and autonomous routine triggers.
- `WikiExportService` (`src/application/web/wiki_export_service.py`) generating formatted markdown documents with YAML frontmatter and enforcing path-jailed security.
- Modern responsive desktop and mobile interface (`src/web/templates/index.html`, `src/web/static/app.js`) with tabbed workflows:
  - 💬 **Interactive Chat**: Live token streaming, reasoning `<think>` toggle bubbles, and real-time tool execution status indicators.
  - 📄 **One-Click Action Buttons**: "Export to Wiki" and "Copy to Clipboard" buttons on both full threads and individual assistant replies.
  - ⏰ **Routines Studio**: Active schedule monitoring, status indicators, and manual "Run Now" execution triggers.
  - 📊 **Observability Dashboard**: High-level platform KPI cards, per-agent resource consumption table, and tool reliability matrix.
  - ⚙️ **Settings Studio**: Live provider model picker, purpose matrix configuration, and interactive hardware RAM fit calculator (with custom specs input for 128GB Nimo PC).
- Observability & KPI Dashboard Backend (`AutoReiv.Observability`): Comprehensive telemetry aggregation, per-agent breakdowns, tool reliability matrices, timeline charts, and structured JSON export.
- `ObservabilityDashboardService` for unified platform KPI calculation (total turns, prompt/completion tokens, avg turn latency, error rate percentage).
- Per-agent segregated KPI breakdown reporting turns, token usage, tool invocations, and error counts.
- `ToolReliabilityMetric` matrix tracking tool call frequencies, failure rates, and average duration.
- Time-series metric aggregation into hourly and customizable timeline buckets.
- `TraceExporter` for structured JSON and session trace dumping without external SaaS dependencies.
- Indexed SQLite analytical queries on `telemetry_spans(agent_id, span_type, created_at)`.
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
