# [CARD-129] Modern Observability, Distributed Tracing & KPI Hardening

> **Status**: In Review
> **Created**: 2026-08-31
> **Spec Reference**: CARD-006; CARD-027; CARD-046; CARD-098
> **Labels**: 	ype:feat, 	ype:quality

---

## 1. Why / Intent
Interaction log audits revealed repeat friction points and observability blindspots:
1. **HITL Approvals Counted as Failures**: Intentional human-in-the-loop safety pauses ( pproval_required) are recorded as success = 0, skewing reliability metrics.
2. **Missing Hierarchical Waterfall Traces**: Spans lack 	race_id and parent_span_id, making it impossible to render parent-to-child waterfall trees during multi-agent handoffs.
3. **Provider & Model Attribution Gap**: Telemetry does not track which specific provider (ollama, openai, gemini,  nthropic) or model produced each span.
4. **Latency Breakdown Gap**: Lack of Time-To-First-Token (	tft_ms) makes it hard to distinguish local host queueing from remote provider inference latency.
5. **Cost & HITL Lifecycle KPIs**: Missing estimated financial cost tracking and approval wait-time metrics.

---

## 2. What to Build
- **Slice 1: HITL Safety Gate Classification**:
  - Update 	elemetry_collector and  gent_kernel so  pproval_required is categorized as hitl_paused with success=True rather than an operational crash.
- **Slice 2: Hierarchical Distributed Tracing**:
  - Add 	race_id and parent_span_id columns to 	elemetry_spans in SQLite and domain TelemetrySpan model.
  - Propagate trace context through StreamTurnKernel, AgentKernel, and HandoffIsolationEngine.
- **Slice 3: Provider & Model Telemetry Attribution**:
  - Store indexed provider and model columns on 	elemetry_spans.
  - Expose provider-level reliability and latency comparisons in get_tool_health_matrix and KPIDashboardSummary.
- **Slice 4: Time-To-First-Token (TTFT) Tracking**:
  - Capture 	tft_ms in OpenAIProviderAdapter, AnthropicProviderAdapter, and OllamaAdapter streaming loops and persist to spans.
- **Slice 5: Cost & HITL Lifecycle KPIs**:
  - Calculate estimated dollar costs ($ / session) using provider pricing presets.
  - Track approval wait duration (time from  pproval_required to human decision) in telemetry.

---

## 3. Acceptance Criteria
- [x] HITL approval pauses no longer register as failures in 	elemetry_spans.
- [x] Multi-agent handoffs and tool calls produce linked spans with matching 	race_id and correct parent_span_id.
- [x] Spans record provider, model, and 	tft_ms.
- [x] Automated tests verify trace propagation and KPI calculation.
- [x] Local commit on qa. Status In Review after implementation.

---

## 4. Constraints
- Work on qa. Do not push unless Jacob explicitly asks.
- Backward compatibility: migration for 	elemetry_spans table schema must not break existing databases.
- Single card in focus.
