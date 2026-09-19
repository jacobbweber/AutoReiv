# Requirements Specification: Observability & KPI Dashboard Backend

> **Spec Status**: Implemented  
> **Target Release**: Milestone 6 (v0.6.0)  
> **Primary Component**: `AutoReiv.Observability`  
> **Applicable ADRs**: `docs/adr/0007-comprehensive-telemetry-aggregation-per-agent-kpis-and-tool-reliability-matrix.md`

---

## 1. Executive Summary & Intent

Milestone 6 implements the **Observability & KPI Dashboard Backend**, enabling real-time inspection of token throughput, agent-by-agent utilization, tool reliability metrics, timeline charts, and full-spectrum trace queries without external third-party telemetry dependencies.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-OBS-001]: Global Platform KPI & Utilization Aggregation
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator requests the platform observability summary THE SYSTEM SHALL calculate aggregated platform KPIs (total turns, prompt tokens, completion tokens, total tokens, average turn duration, error count, and error rate percentage).`
- **Acceptance Criteria**:
  - [ ] Given 10 executed turns with 500 prompt and 200 completion tokens, when querying global KPIs, then total tokens equals 700 and total turns equals 10.
  - [ ] Given 1 failed turn out of 10, when querying global KPIs, then error rate percentage is reported as 10.0%.

### [REQ-OBS-002]: Per-Agent Token & KPI Breakdown
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL aggregate token consumption, turn counts, tool invocations, and error counts segregated by agent profile ID.`
- **Acceptance Criteria**:
  - [ ] Given turns executed across `general-assistant` and `linux-sysadmin`, when querying per-agent metrics, then returns discrete summaries for each agent.

### [REQ-OBS-003]: Tool Execution & Reliability Breakdown
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL track individual tool execution counts, success ratios, failure counts, and average latency across all registered tools.`
- **Acceptance Criteria**:
  - [ ] Given 5 successful executions and 1 failed execution of `cli_exec`, when querying tool reliability, then success rate is 83.33% and failure count is 1.

### [REQ-OBS-004]: Time-Series Telemetry Querying
- **Type**: Event-Driven
- **EARS Statement**: `WHEN requesting timeline metrics THE SYSTEM SHALL aggregate token volume, turn counts, and errors into configurable time buckets (e.g. hourly, daily).`
- **Acceptance Criteria**:
  - [ ] Given spans over multiple hours, when querying time-series data, then results are grouped into chronological time-bucket data points.

### [REQ-OBS-005]: Filtered Trace Inspection & Log Search
- **Type**: Event-Driven
- **EARS Statement**: `WHEN inspecting traces THE SYSTEM SHALL filter spans by agent ID, session ID, span type, error state, and timestamp ranges.`
- **Acceptance Criteria**:
  - [ ] Given spans with and without errors, when querying with `has_error=True`, then only failed spans are returned.

### [REQ-OBS-006]: Structured JSON Trace Export
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator triggers a telemetry export THE SYSTEM SHALL format and return all matching spans as a structured JSON archive.`
- **Acceptance Criteria**:
  - [ ] Given trace spans in SQLite, when exported, then generates a clean, parsable JSON string with all metadata intact.

---

## 3. Non-Functional & Boundary Constraints

- **Query Performance**: Aggregate queries execute in sub-millisecond SQLite time using indexed queries on `telemetry_spans(agent_id, session_id, span_type, start_time)`.
- **Zero External SaaS Dependencies**: All metrics and telemetry calculations run entirely locally within SQLite and Python.
