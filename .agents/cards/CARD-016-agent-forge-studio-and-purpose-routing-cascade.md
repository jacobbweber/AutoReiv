# [CARD-016] Agent Forge Studio and Purpose Routing Cascade

> **Status**: Done
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/agent-forge-and-model-cascade/
> **Labels**: `type:feature`

---

## 1. Why / Intent
Implement dynamic purpose-to-model resolution cascade, full custom agent profile CRUD and persistence, AgentBuilderSkill for System Agent co-pilot, and the Agent Forge Character Sheet SPA interface.

---

## 2. What to Build
Model purpose cascade, custom agent SQLite storage, AgentBuilderSkill, REST agent management endpoints, and Agent Forge Studio UI.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-FORGE-001]: Agent Profiles extended with `purpose`, `avatar_icon`, `is_builtin`, `created_at`, `updated_at`.
- [x] [REQ-FORGE-002]: 3-tier model resolution cascade implemented in `AgentKernel._resolve_model()`.
- [x] [REQ-FORGE-003]: SQLite custom agent persistence table and CRUD operations in `SQLiteStateStore`.
- [x] [REQ-FORGE-004]: Scoped agent tool registry with dynamic permission scoping and baseline protection.
- [x] [REQ-FORGE-005]: `AgentBuilderSkill` equipped with `list_available_skills_and_tools`, `propose_agent_specification`, and `save_agent_specification`.
- [x] [REQ-FORGE-006]: Full Agent Forge Character Sheet UI & System Agent Architect Co-Pilot in Control Plane SPA.
- [x] Automated tests green via `pytest` (194 tests passing).
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
