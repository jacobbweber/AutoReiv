# Technical Design: Granular Telemetry Attribution, Direct Agent & Performance Audit

> **Spec Status**: Approved  
> **Target Release**: CARD-337  
> **Primary Component**: `AutoReiv.Kernel` & `AutoReiv.Observability`

---

## 1. Architecture Overview

This design enhances AutoReiv's telemetry pipeline to measure the "Harness Tax" with sub-turn granularity, introduces a zero-overhead `direct` agent, and equips the `autoreiv` platform agent with an audit tool to publish reports to Wiki Studio.

```
┌─────────────────────────────────────────────────────────────┐
│                       Chat / Routines                       │
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
│                AutoReiv Performance Audit Tool              │
│  Queries spans -> computes efficiency -> hands off to Wiki  │
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

### 2.4 Performance Audit Service & Tool [REQ-AUDIT-001, REQ-AUDIT-002]
In `src/application/observability/audit_service.py`:
- `audit_job(job_id: str) -> PerformanceAuditReport`
- `audit_session(session_id: str) -> PerformanceAuditReport`
- `audit_window(hours: int = 24) -> PerformanceAuditReport`
- `format_markdown_report(report: PerformanceAuditReport) -> str`

Tool registered for `autoreiv` agent in `src/infrastructure/tools/audit_tools.py`:
- `tool.audit_performance_and_cost`

---

## 3. Data Flow & Handoff to Wiki

1. Operator (or Routine) triggers `autoreiv` agent: `"Audit performance for job <id> and publish to wiki"`.
2. `autoreiv` calls `tool.audit_performance_and_cost`.
3. The tool queries `store.get_telemetry_spans()` for that job / session.
4. It aggregates token breakdown and timing into a structured Markdown document and returns it.
5. To persist to the Wiki, `autoreiv` invokes `handoff_to_agent(target_agent_id="wiki", ...)` passing the report.
6. The `wiki` agent calls its `wiki_note_create` tool, filing the note into `00_Inbox/` honoring the One-Door Policy.
7. The scheduled `wiki-curation` routine categorizes and graduates the note to the knowledge warehouse.
