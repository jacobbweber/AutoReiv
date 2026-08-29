# [CARD-066] Unify Agent Handoff To One Public Tool

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/unify-handoff-to-agent/`
> **Labels**: `type:refactor`, `area:orchestration`, `area:kernel`

---

## 1. Why / Intent
Two tools (`delegate_task` and `handoff_to_agent`) and two engines did the same job. Only `delegate_task` was wired to a live kernel. The model could pick the dead door. Caller and session were frozen at bootstrap (`default_session`).

---

## 2. What to Build
- One public tool: `handoff_to_agent`.
- One execution engine: `HandoffIsolationEngine`, with the live kernel injected at app startup.
- Live caller agent id and session id via tool-execution context.
- Keep isolated child sessions, depth/self-handoff guards, and legacy recipient aliases (`sysadmin` → `autoreiv`).
- Stop registering `delegate_task`. Leave `SupervisorOrchestrator` for the REST delegate endpoint and its unit tests.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-010]`: Chat/tool loop exposes only `handoff_to_agent` for agent-to-agent delegation.
- [x] `[REQ-ORCH-011]`: Handoff engine has a kernel after `create_app`.
- [x] `[REQ-ORCH-012]`: Child session id is derived from the live parent session, not `default_session`.
- [x] Automated tests green via `pytest` on touched suites.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- Do not flatten child turns into the parent transcript.
- Do not invent a third orchestration stack.
