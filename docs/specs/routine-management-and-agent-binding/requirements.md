# Requirements: Routine Management and Agent Binding

> **Standard**: AWS Kiro EARS (Easy Approach to Requirements Syntax)  
> **Traceability Prefix**: `[REQ-ROUT-xxx]`  
> **Target Component**: `AutoReiv.Routines` & `AutoReiv.Web`

---

## 1. System Context & User Stories

As an **Operator**,  
I want to **create, edit, schedule, pause/resume, and delete autonomous routines via the Web UI**,  
And I want to **view both exact cron expressions and human-friendly scheduled intervals with next run times**,  
And I want to **inspect which active routines are tethered to each agent directly within their Agent Forge character sheet**,  
So that **standing background jobs and multi-agent autonomous missions can be managed seamlessly with zero cognitive friction**.

---

## 2. EARS Requirements Specification

### [REQ-ROUT-001]: Dual Cron Syntax & Human-Readable Schedule Translation
- **Type**: Ubiquitous / Responsive
- **Statement**: The system shall parse cron expressions (e.g., `0 * * * *`, `*/15 * * * *`, `0 8 * * *`) and provide bidirectional human-readable schedule summaries (e.g., *"Every hour at minute 0"*, *"Every 15 minutes"*, *"Every day at 08:00 UTC"*) and compute the exact next execution timestamp.

### [REQ-ROUT-002]: Full Routine Lifecycle REST API (CRUD & Pause/Resume)
- **Type**: Ubiquitous
- **Statement**: The system shall expose REST API endpoints (`GET /api/routines`, `POST /api/routines`, `PUT /api/routines/{id}`, `DELETE /api/routines/{id}`, `POST /api/routines/{id}/toggle`) allowing callers to create custom routines, update schedules/directives, toggle enabled/paused status, and delete custom routines while preserving built-in baseline routines.

### [REQ-ROUT-003]: Lead-Agent Routine Binding & Filtered Queries
- **Type**: State-Driven
- **Statement**: While querying routines, the system shall support filtering by `agent_id` (`GET /api/routines?agent_id={id}`) and return all active or paused standing routines assigned to that specific agent.

### [REQ-ROUT-004]: Routines Studio Management UI & Modal Editor
- **Type**: Event-Driven
- **Statement**: When an operator navigates to the Routines Studio tab in the Control Plane SPA, the UI shall render routine cards with live status badges, human-readable schedules, last run telemetry, a `[+ New Routine]` modal with cron preset selectors, `[▶️ Run Now]`, `[✏️ Edit]`, `[⏸️ Pause/Resume]`, and `[🗑️ Delete]` controls.

### [REQ-ROUT-005]: Agent Forge "Assigned Routines" Character Sheet Integration
- **Type**: State-Driven
- **Statement**: When an agent profile is selected in the Agent Forge Studio, the character sheet shall render a dedicated `[⏰ Assigned Background Routines]` card displaying all standing jobs linked to that agent, with direct action links to trigger or edit the routine.
