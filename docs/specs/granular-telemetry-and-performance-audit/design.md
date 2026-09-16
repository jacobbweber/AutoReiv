# Technical Design: Granular Telemetry Attribution, Direct Agent & Performance Audit

> **Spec Status**: Approved  
> **Target Release**: CARD-337  
> **Primary Component**: `AutoReiv.Kernel` & `AutoReiv.Observability`

---

## 1. Architecture Overview

This design enhances AutoReiv's telemetry pipeline to measure the "Harness Tax" with sub-turn granularity, introduces a zero-overhead `direct` agent, and surfaces deterministic session audit and report generation directly in Observe Studio without burning LLM inference tokens.

```
┌─────────────────────────────────────────────────────────────┐
│                         Chat Studio                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         AgentKernel                         │
│  1. Measures raw user prompt                                │
│  2. Resolves persona, tool schemas, skills, memory          │
│  3. Isolates token attribution for each slice               │
│  4. Tracks prep_ms -> TTFT -> generation_ms                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     MultiProviderGateway                    │
│  Dispatches to active provider (vLLM, Ollama, Cloud)        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    TelemetrySpan (SQLite)                   │
│  `metadata_json` stores:                                    │
│    - token_breakdown (user, tools, persona, memory, skills) │
│    - timing_breakdown (prep, ttft, gen, speed, inter_step)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             AuditService & Observe Studio UI                │
│  - GET /api/observability/sessions?agent_id=<id>            │
│  - GET /api/observability/audit?session_id=<id>             │
│  - POST /api/observability/audit/export -> 00_Inbox/        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Direct Agent Manifest [REQ-TEL-001]
Lives in `platform-packs/direct/agent.json` (and user-data copy):
```json
{
  "id": "direct",
  "name": "Direct",
  "role": "Direct LLM Pass-Through",
  "system_prompt": "You are a direct, concise assistant.",
  "tools": [],
  "skills": [],
  "provider": "default",
  "model": "default"
}
```

### 2.2 Granular Token Attribution Model [REQ-TEL-002, REQ-TEL-003]
Stored in `telemetry_spans.metadata_json`:
```json
{
  "token_breakdown": {
    "user_prompt": 63,
    "agent_persona": 720,
    "tool_schemas": 3150,
    "progressive_skills": 410,
    "episodic_memory": 280,
    "compacted_history": 326,
    "tool_results_injected": 0,
    "completion": 88,
    "reasoning": 127
  },
  "timing_breakdown": {
    "harness_prep_ms": 4.5,
    "ttft_ms": 1820.0,
    "generation_ms": 7450.0,
    "tokens_per_second": 11.8,
    "inter_step_latency_ms": 42.0,
    "total_round_trip_ms": 9316.5
  },
  "step_context": {
    "job_id": "job_123",
    "phase_id": "phase_456",
    "phase_name": "Formulate",
    "phase_index": 0
  }
}
```

### 2.3 Fast Token Attribution Calculator
In `src/application/kernel/telemetry_attribution.py`:
```python
def calculate_token_attribution(
    user_prompt: str,
    system_prompt: str,
    tool_definitions: Optional[Sequence[ToolDefinition]],
    skill_bodies: Optional[Sequence[str]],
    memory_facts: Optional[Sequence[str]],
    history_messages: Optional[Sequence[ChatMessage]],
    tool_results: Optional[Sequence[str]],
    completion_content: str,
    reasoning_content: Optional[str] = None,
) -> TokenBreakdown:
    ...
```

### 2.4 Deterministic Performance Audit Service [REQ-AUDIT-001]
In `src/application/observability/audit_service.py`:
- `audit_job(job_id: str) -> PerformanceAuditReport`
- `audit_session(session_id: str) -> PerformanceAuditReport`
- `audit_window(hours: int = 24) -> PerformanceAuditReport`
- `format_markdown_report(report: PerformanceAuditReport) -> str`

### 2.5 Observe Studio Telemetry Audit & Inbox Export [REQ-AUDIT-002]
In `src/web/routers/observability.py`:
- `GET /api/observability/sessions?agent_id=<id>`: Returns recent chat sessions for the selected agent.
- `GET /api/observability/audit?session_id=<id>`: Returns aggregated token breakdown, timing stats, scaffold ratio, and estimated cost.
- `POST /api/observability/audit/export`: Deterministically formats the report and calls `wiki_service.create_note` with title `"telemetry-audit-<session_id>"`, filing it into `00_Inbox/` with initial YAML frontmatter (`topic: performance`, `domain: engineering`).

In `src/web/templates/index.html` & `src/web/static/modules/studios/observability.js`:
- `#observeSessionSelect`: Populated dynamically when an agent is selected.
- `#observeAuditContainer`: Renders KPI summary cards (Scaffold Ratio, Prompt/Completion, Est Cost, Avg TTFT, Speed), Tool Bloat alerts, and component token attribution breakdown table.
- `#observeGenerateReportBtn`: Triggers one-click export to Wiki inbox without LLM intervention.

---

## 3. Data Flow & Deterministic Inbox Export

1. Operator opens Observe Studio and selects an Agent (e.g. `autoreiv` or `direct`).
2. Observe Studio fetches recent sessions via `GET /api/observability/sessions?agent_id=<id>` and populates `#observeSessionSelect`.
3. Selecting a session requests `GET /api/observability/audit?session_id=<id>`.
4. `AuditService` queries `store.get_telemetry_spans()` for all turns in that session, calculates the component breakdowns, scaffold ratio, and cost.
5. The UI renders the live cards and breakdown table.
6. When the operator clicks **"Generate Report to Inbox"**, the client calls `POST /api/observability/audit/export`.
7. The endpoint deterministically renders markdown using `format_markdown_report` and commits the note to `00_Inbox/<slug>.md` via `wiki_service.create_note` honoring the One-Door Policy (zero LLM token burn).
8. The scheduled `wiki-curation` routine later categorizes, enriches, and moves the report to its permanent vault location.
