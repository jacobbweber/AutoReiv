# [CARD-011] Multi-Agent Handoff Protocol and Supervisor Orchestration

> **Status**: Completed
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/multi-agent-handoff-and-orchestration/
> **Labels**: `type:feature`

---

## 1. Why / Intent
Enable multi-agent collaboration via a structured 5-key A2A handoff envelope, supervisor-worker delegation engine, and live streaming handoff badges.

---

## 2. What to Build
HandoffEnvelope model, SupervisorOrchestrator with recursion guardrails, DelegateSubtaskSkill tool registration, streaming handoff indicators in Chat Studio, and handoff telemetry spans.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-A2A-001]: Standardized 5-Key A2A Handoff Envelope (`sender_agent_id`, `recipient_agent_id`, `session_id`, `task_intent`, `context_payload`, `correlation_id`).
- [x] [REQ-A2A-002]: Supervisor Delegation Engine with recursion depth bounding (max 2 tiers), circular self-handoff prevention, and child session isolation.
- [x] [REQ-A2A-003]: Delegate Subtask Tool & Skill (`DelegateSubtaskSkill.register_tools`) exposing `delegate_task` to agents.
- [x] [REQ-A2A-004]: Inter-Agent Context Hydration with working memory facts and payload mapping.
- [x] [REQ-A2A-005]: Inter-Agent Telemetry & Correlation Tracing recording `handoff` spans in `TelemetryCollector`.
- [x] [REQ-A2A-006]: REST Multi-Agent Delegation API (`POST /api/agents/delegate`).
- [x] [REQ-A2A-007]: Chat Stream & UI Live Handoff Indicators with animated badge in Chat Studio.
- [x] Automated tests green via `pytest` (314 passing) and `vitest` (50 passing).
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

