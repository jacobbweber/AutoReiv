# Requirements Specification: Agent Kernel, Scoped Memory & Telemetry Engine

> **Spec Status**: Implemented  
> **Target Release**: Milestone 2 (v0.2.0)  
> **Primary Component**: `AutoReiv.Kernel`, `AutoReiv.Memory`, `AutoReiv.Telemetry`  
> **Applicable ADRs**: `docs/adr/0003-agent-kernel-scoped-tool-registry-and-sqlite-state-persistence.md`

---

## 1. Executive Summary & Intent

Milestone 2 establishes the core agent execution kernel, scoped tool authorization system, SQLite-backed conversation state checkpointer, and observability telemetry engine. It enables specialized agents (e.g. General Assistant, Linux Sysadmin, Librarian, System Agent) to run iterative ReAct decision loops with strict tool access control, persistent conversation histories, and full execution tracing.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-KERNEL-001]: Agent Profile & Persona Manifest
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL represent agents as declarative profiles specifying unique identifier, name, description, system prompt, tone, model identifier, and authorized tool permissions.`
- **Acceptance Criteria**:
  - [ ] Given a valid agent configuration, when loaded into an `AgentProfile`, then all identity, prompt, and tool permission fields are validated.
  - [ ] Given an agent with a configured tone (e.g. `'concise'`, `'technical'`, `'friendly'`), when formatting the prompt, then the appropriate tone directive is injected into the system prompt.
  - [ ] Given an invalid or empty agent ID, when instantiated, then it raises `AgentValidationError`.

### [REQ-KERNEL-002]: Scoped Tool Registry & RBAC Permissions
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent attempts to execute a tool THE SYSTEM SHALL verify tool authorization against the agent profile and deny unauthorized execution with a permission error.`
- **Acceptance Criteria**:
  - [ ] Given an agent authorized for `["task_tracker"]` attempting to invoke `task_tracker`, when executed, then the tool runs successfully and returns `ToolResult`.
  - [ ] Given an agent attempting to invoke an unauthorized tool (e.g. `cli_exec` when only authorized for `task_tracker`), when executed, then the registry denies execution and returns a structured permission error without executing the underlying function.
  - [ ] Given an unknown tool name, when dispatched, then it returns a `ToolNotFoundError`.

### [REQ-KERNEL-003]: Iterative ReAct Execution Loop & Budgeting
- **Type**: State-Driven
- **EARS Statement**: `WHILE an agent turn requires tool execution THE SYSTEM SHALL iteratively execute tools, append tool responses to conversation history, and query the LLM gateway until completion or until turn budget/cycle limits are reached.`
- **Acceptance Criteria**:
  - [ ] Given a user query requiring multiple tool calls, when processed by `AgentKernel`, then the loop resolves each tool call and returns the final assistant answer.
  - [ ] Given an execution reaching `max_turns` (default 10), when reached, then the loop gracefully terminates with finish reason `"max_turns"`.
  - [ ] Given repetitive identical tool calls (cycle detected), when identified, then the loop stops and returns the best available partial response.

### [REQ-KERNEL-004]: SQLite WAL Session & Message Persistence
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist chat sessions and chronological message histories in a WAL-mode SQLite database isolated per session and agent.`
- **Acceptance Criteria**:
  - [ ] Given a new conversation session, when `create_session(agent_id, title)` is called, then a persistent session record is created in SQLite with WAL mode enabled.
  - [ ] Given messages sent during an agent turn, when `save_message()` is called, then messages are persisted with role, content, tool calls, and sequential ordering.
  - [ ] Given an existing session ID, when `get_messages(session_id)` is called, then all messages are reloaded in exact chronological sequence.

### [REQ-KERNEL-005]: Telemetry Spans & Reliability Tracking
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent turn or tool execution occurs THE SYSTEM SHALL record execution duration, token counts, and success/failure status into persistent telemetry records.`
- **Acceptance Criteria**:
  - [ ] Given a completed agent turn, when finished, then a telemetry span is stored recording `agent_id`, `session_id`, `duration_ms`, `prompt_tokens`, `completion_tokens`, and status.
  - [ ] Given a tool execution failure, when caught, then the telemetry record captures the error message and tool name with `success=False`.
  - [ ] Given telemetry records in the database, when queried via `get_agent_metrics()` or `get_tool_metrics()`, then aggregated counts, average latency, and success rates are returned.

### [REQ-KERNEL-006]: Streaming Step Events & Progress Callbacks
- **Type**: Event-Driven
- **EARS Statement**: `WHEN streaming agent execution THE SYSTEM SHALL emit structured events for text deltas, tool invocation starts, tool outputs, and final completion status.`
- **Acceptance Criteria**:
  - [ ] Given a streaming execution request, when tools are invoked, then the kernel yields `KernelEvent` items containing event type (`"token"`, `"tool_start"`, `"tool_end"`, `"done"`).
  - [ ] Given a token event, when yielded, then it contains the incremental text and reasoning delta.

---

## 3. Non-Functional & Boundary Constraints

- **Thread-Safe / Async-Safe SQLite**: Database access uses a robust connection pool / async wrapper with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`.
- **Hermetic Testing**: Unit tests run against an in-memory SQLite database (`:memory:`) or temporary files with zero leftover state.
- **DIP Boundaries**: Domain entities (`AgentProfile`, `ToolResult`, `KernelEvent`) have zero external database or HTTP dependencies.

---

## 4. Out of Scope

- Specific tool implementations for the 4 agents (e.g. PARA file parser, bash runner) - specified and implemented in Milestone 3.
- Background cron scheduling daemon - implemented in Milestone 4.
- Web UI frontend controls - implemented in Milestone 7.
