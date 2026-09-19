# Requirements: Visual Goal Mode & Reflexion Streaming

## Feature Overview
Provides unified Server-Sent Events (SSE) streaming for multi-step Goal Planning (`PlanAndExecuteEngine`) and Self-Verification (`ReflexionLoopEngine`), coupled with an interactive real-time visual milestone progress tracker and reflexion badge in the AutoReiv Chat Studio UI.

---

## 1. Functional Requirements (EARS Format)

### [REQ-CHAT-010] Unified Chat Stream Payload Parameters
- **EARS Statement**: `WHEN a client submits a POST request to /api/chat/stream, THE SYSTEM SHALL accept optional boolean parameters "goal_mode" (default: false) and "self_verify" (default: false) alongside agent_id, session_id, and content.`
- **Acceptance Criteria**:
  - [ ] Given a valid `ChatStreamRequest`, when `goal_mode=false` and `self_verify=false`, the standard single-turn streaming ReAct loop executes.
  - [ ] Given `goal_mode=true`, the kernel routes the turn through `PlanAndExecuteEngine` and streams milestone events.
  - [ ] Given `self_verify=true`, the kernel executes turns with critique-guided verification assertions.

### [REQ-CHAT-011] Plan & Milestone Server-Sent Stream Events
- **EARS Statement**: `WHERE goal_mode is enabled, THE SYSTEM SHALL stream structured "plan_formulated", "step_start", and "step_complete" SSE events containing plan IDs, step titles, step indices, and milestone descriptions.`
- **Acceptance Criteria**:
  - [ ] `plan_formulated` event contains `{ plan_id: str, goal: str, steps: [{ title: str, description: str }] }`.
  - [ ] `step_start` event contains `{ step_index: int, title: str }`.
  - [ ] `step_complete` event contains `{ step_index: int, status: "completed" | "failed" }`.

### [REQ-CHAT-012] Reflexion Self-Verification Stream Events
- **EARS Statement**: `WHERE self_verify is enabled, THE SYSTEM SHALL stream "reflexion_attempt", "reflexion_critique", and "reflexion_verified" SSE events containing attempt counters, assertion results, and critique feedback.`
- **Acceptance Criteria**:
  - [ ] `reflexion_attempt` event emits `{ attempt: int, max_attempts: int }`.
  - [ ] `reflexion_critique` event emits `{ attempt: int, critique: str }` when verification criteria fail.
  - [ ] `reflexion_verified` event emits `{ attempt: int, passed: true }` upon successful validation.

### [REQ-CHAT-013] Chat Studio Interactive Milestone DAG Widget
- **EARS Statement**: `WHEN receiving plan and step SSE events in Chat Studio, THE CLIENT SHALL render a visual milestone progress box displaying active step spinner, completed checkmarks, and live step descriptions.`
- **Acceptance Criteria**:
  - [ ] Renders a distinct card at the top of the streaming message bubble showing all formulated steps.
  - [ ] Active step is highlighted with an animated pulsing icon.
  - [ ] Completed steps display green checkmarks and duration.

### [REQ-CHAT-014] Dual-Mode Combined Execution (Goal + Verify)
- **EARS Statement**: `WHEN both goal_mode and self_verify are enabled, THE SYSTEM SHALL execute each decomposed milestone step under the Reflexion verification loop before marking the milestone complete.`
- **Acceptance Criteria**:
  - [ ] Each step runs up to 3 refinement attempts if criteria fail.
  - [ ] Synthesis deliverable is presented as the final verified response.
