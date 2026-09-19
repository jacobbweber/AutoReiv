# Requirements Specification: Dual Engine Front Door (AutoReiv Core & Direct Mode)

> **Spec Status**: Approved (Draft for Review)  
> **Target Release**: v0.18.0 (Milestone 18 — Autonomic OS & Mechanical Governance)  
> **Primary Component**: Chat Studio Frontend (`chat.js`, `index.html`) & Chat Router (`src/web/routers/chat.py`)  
> **Grounding**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [CARD-361](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-361-dual-engine-front-door-autoreiv-core-and-direct-mode.md)

---

## 1. Executive Summary & Intent

Per ADR-0054, multi-agent conversational roundtables (CARD-340) and superficial persona dropdowns introduce token explosion (16k token schema tax), catastrophic handoff latency, and cognitive confusion. Foundation model intelligence is grounded in parametric weights, tools, and skills.

Chat Studio establishes a **Dual-Engine Front Door** consisting of two explicit operating modes:
1. **AutoReiv Core (`autoreiv`)**: The primary state-machine orchestrator (`JobPhaseOrchestrator`) executing phased workflows with catalog capability resolution, demand-paged tools, grounded context, and mechanical verification.
2. **Direct Mode (`direct`)**: A raw, unconstrained conversational LLM pass-through with zero tool schemas, zero orchestrator overhead, and instant streaming.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-CHAT-DUAL-001]: Dual-Engine Front Door Control
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide a dual-engine front door in Chat Studio with exactly two operating channels: AutoReiv Core (primary state-machine orchestrator) and Direct Mode (raw conversational LLM stream), retiring persona dropdown rosters from Chat Studio.`
- **Acceptance Criteria**:
  - [ ] Given Chat Studio is loaded, the top bar presents a segmented dual-engine control with **AutoReiv Core** and **Direct Mode**.
  - [ ] Given an agent list from `GET /api/agents`, `agentsVisibleInChat` filters the selectable roster to strictly `autoreiv` and `direct`.
  - [ ] Given `#agentSelect` exists in markup for test compatibility, switching the engine toggle updates `#agentSelect.value` and vice versa.

### [REQ-CHAT-DUAL-002]: Direct Mode Fast-Path Execution Bypass
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a chat turn is submitted under Direct Mode (agent_id='direct'), THE SYSTEM SHALL bypass JobPhaseOrchestrator, job record creation, catalog capability resolution, and phase lifecycle events, streaming completion tokens directly from the LLM provider with zero tool schemas.`
- **Acceptance Criteria**:
  - [ ] Given a stream request with `agent_id == 'direct'`, `chat_stream` does not invoke `orch.create_job_from_catalog_resolve`.
  - [ ] Zero `Job` or `Phase` database rows are inserted into the SQLite store for direct turns.
  - [ ] The LLM completion request sends `tools=None`, eliminating the prompt token schema tax.
  - [ ] SSE stream delivers `token` and `turn_done` events with `direct_mode: true`.
  - [ ] User and assistant messages are persisted to session history.

### [REQ-CHAT-DUAL-003]: AutoReiv Core State-Machine Orchestration
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a chat turn is submitted under AutoReiv Core (agent_id='autoreiv'), THE SYSTEM SHALL execute through JobPhaseOrchestrator with catalog capability resolution, phase lifecycle tracking, and verification gates.`
- **Acceptance Criteria**:
  - [ ] Given a stream request with `agent_id == 'autoreiv'`, a standing `Job` is created and managed through `JobPhaseOrchestrator`.
  - [ ] SSE stream delivers `job_created`, `phase_start`, `phase_complete`, and react state events.

### [REQ-CHAT-DUAL-004]: Scoped Session Continuity & Engine Switching
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator switches between AutoReiv Core and Direct Mode, THE SYSTEM SHALL reload the session drawer filtered to the active engine channel and update active session title and header indicators.`
- **Acceptance Criteria**:
  - [ ] Clicking **Direct Mode** switches active channel to `direct`, persists `autoreiv_active_agent_id = 'direct'`, and loads direct sessions.
  - [ ] Clicking **AutoReiv Core** switches active channel to `autoreiv`, persists `autoreiv_active_agent_id = 'autoreiv'`, and loads core sessions.
  - [ ] Creating a new session under Direct Mode initializes session title as `Direct Chat`.

### [REQ-CHAT-DUAL-005]: Direct Mode Status & Chrome Suppression
- **Type**: State-Driven
- **EARS Statement**: `WHILE Direct Mode is active, THE SYSTEM SHALL suppress the Job/Phase status strip and inline job chrome tiles, displaying a lightweight direct streaming indicator with zero tool overhead.`
- **Acceptance Criteria**:
  - [ ] While in Direct Mode, `#jobPhaseStatusStrip` remains hidden.
  - [ ] In Direct Mode, streaming does not create or render inline job phase chrome blocks.
  - [ ] Top bar header displays active engine badge: `⚡ AutoReiv Core (Orchestrated)` or `💬 Direct Mode (Zero Tools)`.

---

## 3. Non-Functional & Boundary Constraints

- **Latency**: Direct Mode Time to First Token (TTFT) should be sub-second on local models by avoiding schema pre-fill.
- **Fail-Safe**: If `job_orchestrator` is uninitialized or in degraded state, Direct Mode must continue to operate without throwing 500 errors.
- **Backward Compatibility**: Existing automated Playwright tests and unit tests referencing `#agentSelect` must continue to pass cleanly.

---

## 4. Out of Scope

- Dynamic demand-paging of tool subsets (owned by **CARD-362**).
- Mechanical linter for `SKILL.md` (owned by **CARD-363**).
- Telemetry detectors and proposal inbox (owned by **CARD-364** and **CARD-365**).
