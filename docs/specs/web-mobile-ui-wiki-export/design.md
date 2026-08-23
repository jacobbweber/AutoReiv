# Technical Design: Responsive Web & Mobile Front-Door with Wiki Export

> **Linked Spec**: [`requirements.md`](./requirements.md)  
> **Applicable ADRs**: [`docs/adr/0008-fastapi-web-application-rest-streaming-api-and-responsive-multi-view-spa.md`](../../adr/0008-fastapi-web-application-rest-streaming-api-and-responsive-multi-view-spa.md)

---

## 1. Architectural Overview & Workflow

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Client (Desktop & Mobile SPA)"]
        ChatView["Interactive Chat (Tokens, <think>, Tool Badges)"]
        WikiBtn["'Export to Wiki' & 'Copy' Action Buttons"]
        SettingsView["Settings Studio (Model Picker & Hardware RAM Slider)"]
        KPIView["Observability Dashboard (Metric Cards & Leaderboards)"]
        RoutinesView["Routines Management & 'Run Now' Triggers"]
    end

    subgraph FastAPIServer["FastAPI Backend (src/web/app.py)"]
        SSEEndpoint["/api/chat/stream (SSE Stream)"]
        WikiEndpoint["/api/export/wiki (Wiki Export API)"]
        SettingsEndpoints["/api/settings/* (Discovery, Purpose Matrix)"]
        KPIEndpoints["/api/observability/* (Metrics, Traces)"]
        RoutineEndpoints["/api/routines/* (List, Trigger)"]
    end

    subgraph CoreApplication["AutoReiv Application Layer"]
        Kernel["AgentKernel (ReAct Loop)"]
        WikiService["WikiExportService"]
        SettingsService["SettingsService"]
        ObsService["ObservabilityDashboardService"]
        RoutineExecutor["RoutineExecutor"]
        StateStore[("SQLiteStateStore")]
    end

    ChatView -->|EventSource / POST SSE| SSEEndpoint
    WikiBtn -->|POST Payload| WikiEndpoint
    SettingsView -->|GET/POST| SettingsEndpoints
    KPIView -->|GET Metrics| KPIEndpoints
    RoutinesView -->|POST Trigger| RoutineEndpoints

    SSEEndpoint --> Kernel
    WikiEndpoint --> WikiService
    SettingsEndpoints --> SettingsService
    KPIEndpoints --> ObsService
    RoutineEndpoints --> RoutineExecutor
```

---

## 2. API Contract & Schemas

### Chat Stream Request (`POST /api/chat/stream`)
```json
{
  "agent_id": "general-assistant",
  "session_id": "sess-123",
  "content": "Synthesize today's high-priority tasks."
}
```

### Server-Sent Events Protocol
- `event: token` $\rightarrow$ `data: {"text": "Hello"}`
- `event: reasoning` $\rightarrow$ `data: {"text": "Analyzing tasks..."}`
- `event: tool_start` $\rightarrow$ `data: {"tool_name": "task_tracker_list", "arguments": {}}`
- `event: tool_output` $\rightarrow$ `data: {"tool_name": "task_tracker_list", "result": "..."}`
- `event: turn_done` $\rightarrow$ `data: {"content": "...", "duration_ms": 320.0, "total_tokens": 140}`

### Wiki Export Request (`POST /api/export/wiki`)
```json
{
  "title": "Morning Briefing - 2026-08-22",
  "content": "...",
  "agent_id": "general-assistant",
  "session_id": "sess-123",
  "category": "03_Resources",
  "tags": ["briefing", "daily"]
}
```
- **Response**:
```json
{
  "status": "success",
  "filepath": "data/wiki/03_Resources/morning_briefing_2026_08_22.md",
  "filename": "morning_briefing_2026_08_22.md"
}
```

---

## 3. Wiki Note File Format Structure

```markdown
---
title: "Morning Briefing - 2026-08-22"
agent: "general-assistant"
session_id: "sess-123"
exported_at: "2026-08-22T22:55:00Z"
tags:
  - "briefing"
  - "daily"
---

# Morning Briefing - 2026-08-22

[Markdown Conversation or AI Response Body]
```
