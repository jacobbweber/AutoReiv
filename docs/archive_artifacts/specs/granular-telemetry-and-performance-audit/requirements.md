# Requirements Specification: Granular Telemetry Attribution, Direct Agent & Performance Audit

> **Spec Status**: Approved  
> **Target Release**: CARD-337  
> **Primary Component**: `AutoReiv.Kernel` & `AutoReiv.Observability`

---

## 1. Executive Summary & Intent

AutoReiv injects rich context on every turn (persona, tool JSON schemas, progressive skills, episodic memory facts, compacted history). This "harness tax" expands a 60-token user prompt into 5,000 tokens of input, increasing Time-To-First-Token (TTFT), KV-cache memory pressure on local hardware (Nvidia Spark, Nimo PC), and cloud token costs.

Currently, `telemetry_spans.prompt_tokens` logs only a single lump-sum number. Operators cannot isolate which subsystem caused bloat (tool schemas vs persona vs memory vs tool dumps), nor can they run a pure zero-tool baseline conversation.

This specification defines:
1. A built-in platform agent **`direct`** with zero tools and zero skills for clean model baseline comparisons.
2. Granular token attribution and timing telemetry stored in `telemetry_spans.metadata_json` on every turn.
3. A deterministic **Performance & Cost Audit Service** that calculates token distribution, scaffold overhead ratio ("Harness Tax"), and dollar cost estimates without burning LLM inference tokens.
4. An **Observe Studio Telemetry Audit Interface** featuring agent-to-session dynamic history browsing, real-time attribution breakdown, tool bloat alerts, and one-click markdown report export directly into the Wiki staging inbox (`00_Inbox/`).

---

## 2. User Stories & EARS Functional Requirements

### [REQ-TEL-001]: Platform Direct Agent
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide a built-in platform agent named 'direct' with an empty tool registry, empty skills list, and a minimal single-sentence system prompt.`
- **Acceptance Criteria**:
  - [x] Agent profile `direct` is seeded and discoverable in the agent registry.
  - [x] Invocations with `agent_id="direct"` mount zero tools (`req.tools = None`).
  - [x] Invocations with `agent_id="direct"` inject zero progressive skills.

### [REQ-TEL-002]: Granular Token Attribution Telemetry
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an LLM turn is assembled and executed THE SYSTEM SHALL record discrete token counts for each constituent prompt section inside telemetry_spans.metadata_json.`
- **Acceptance Criteria**:
  - [x] `metadata_json` includes a `token_breakdown` dictionary with keys:
    - `user_prompt`
    - `agent_persona`
    - `tool_schemas`
    - `progressive_skills`
    - `episodic_memory`
    - `compacted_history`
    - `tool_results_injected`
    - `completion`
    - `reasoning` (when present)
  - [x] For `direct` agent turns, `tool_schemas` equals 0 and `scaffold_overhead_ratio` is minimal.
  - [x] Total prompt tokens matches the sum of the input breakdown components.

### [REQ-TEL-003]: Turn Timing Stage Telemetry
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an LLM turn executes THE SYSTEM SHALL record timing stages inside telemetry_spans.metadata_json.`
- **Acceptance Criteria**:
  - [x] `metadata_json` includes a `timing_breakdown` dictionary with keys:
    - `harness_prep_ms` (time to resolve skills, compact context, format tools)
    - `ttft_ms` (time to first token from provider)
    - `generation_ms` (time from first token to stream termination)
    - `tokens_per_second` (effective generation speed)
    - `inter_step_latency_ms` (time between previous phase finish and current phase start)
    - `total_round_trip_ms`

### [REQ-AUDIT-001]: Deterministic Performance & Cost Audit Service
- **Type**: Event-Driven
- **EARS Statement**: `WHEN requested with a job_id, session_id, or time window THE SYSTEM SHALL query telemetry_spans, calculate token distribution, latency metrics, scaffold overhead ratio, and dollar cost estimates, and format a comprehensive Markdown performance audit report.`
- **Acceptance Criteria**:
  - [x] Given a valid `job_id` or `session_id`, the service aggregates all turns, token breakdown components, TTFT, TPS, and total cost.
  - [x] Given an `hours` parameter, the service aggregates all turns in the time window and identifies top token consumers and slowest phases.
  - [x] Flags actionable warnings when `tool_schemas` exceeds 50% of prompt tokens or when prep overhead exceeds 500ms.
  - [x] Executes deterministically in `< 50ms` with zero LLM inference cost.

### [REQ-AUDIT-002]: Observe Studio Session Audit & Inbox Export
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator inspects an agent in Observe Studio THE SYSTEM SHALL populate recent chat sessions, display the granular token and timing breakdown, and provide a one-click export action that saves the report to the Wiki inbox (00_Inbox/) honoring the One-Door Policy.`
- **Acceptance Criteria**:
  - [x] Selecting an agent populates `#observeSessionSelect` with recent chat sessions via `GET /api/observability/sessions?agent_id=<id>`.
  - [x] Selecting a session renders real-time Scaffold Ratio, Prompt vs Completion counts, Est Cost, Avg TTFT, speed, and token breakdown table via `GET /api/observability/audit?session_id=<id>`.
  - [x] Clicking `#observeGenerateReportBtn` invokes `POST /api/observability/audit/export`, filing `00_Inbox/telemetry-audit-<session_id>.md` with initial YAML frontmatter.
  - [x] No LLM agent tools or scheduled routines are required for deterministic telemetry reporting.

---

## 3. Non-Functional & Boundary Constraints

- **Performance**: Computing token breakdown and timing attribution overhead must be `< 1ms` per turn.
- **Reliability**: Fail-soft token calculation: if token estimation fails, fallback gracefully to total length approximation without breaking the turn.
- **Schema Safety**: `telemetry_spans.metadata_json` carries the new payloads without requiring a destructive database schema migration.

---

## 4. Out of Scope

- Real-time animated token charts in Chat Studio (handled by existing Debug inspector CARD-136).
- Custom tokenizer training or downloading external tokenizers (uses standard fast character/word token approximation).
