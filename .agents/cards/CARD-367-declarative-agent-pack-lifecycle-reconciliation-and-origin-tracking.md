# [CARD-367] Declarative Agent Pack Lifecycle Reconciliation and Origin Tracking

> **Status**: Done
> **Created**: 2026-09-19
> **Spec Reference**: docs/specs/pack-lifecycle-reconciliation/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Eliminate AppData ghost packs and prevent stale custom agent drift by introducing an explicit origin taxonomy (PLATFORM, SYSTEM, CUSTOM) and a declarative desired-state reconciliation engine that automatically purges abandoned platform seeds on startup.

---

## 2. What to Build
1. Add origin column to SQLite custom_agents table and AgentProfile domain model (PLATFORM, SYSTEM, CUSTOM). 2. Implement DeclarativePackReconciler in src/infrastructure/skills/reconciler.py comparing desired PLATFORM_PACK_IDS against actual AppData state on boot. 3. Update auto-discovery loop to ignore packs without user_managed flag. 4. Author comprehensive tests verifying zero ghost resurrections.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-RECON-001]`: `AgentOrigin` enum (`PLATFORM`, `SYSTEM`, `CUSTOM`) defined in domain models and persisted via `origin` column in SQLite `custom_agents` and `agent_overrides` tables.
- [x] `[REQ-RECON-002]`: `DeclarativePackReconciler` compares desired `PLATFORM_PACK_IDS` against AppData state on boot, automatically purging retired platform seeds from disk and SQLite.
- [x] `[REQ-RECON-003]`: User custom agents (`origin == CUSTOM`) are strictly preserved and never mutated or deleted by platform sync.
- [x] `[REQ-RECON-004]`: Auto-import discovery loop will not resurrect unmanaged or retired pack directories into SQLite.
- [x] `[REQ-RECON-005]`: `/api/agents` returns `origin` field for all agents, and `DELETE /api/agents/{id}` protects platform and system agents.
- [x] Automated tests green via `pytest` and Vitest.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
