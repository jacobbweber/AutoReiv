# Implementation Tasks: Declarative Agent Pack Lifecycle Reconciliation & Origin Tracking

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference corresponding `[REQ-RECON-xxx]` tags.  

---

## Vertical Slice Breakdown

### Slice 1: Origin Taxonomy & Schema Migration
- [x] **Task 1.1** `[REQ-RECON-001]`: [RED] Write unit tests in `tests/unit/agents/test_agent_origin_taxonomy.py` verifying `AgentOrigin` enum, `AgentProfile.origin` field defaults, and serialization.
- [x] **Task 1.2** `[REQ-RECON-001]`: [GREEN] Add `AgentOrigin` enum to `src/domain/kernel/models.py` (`PLATFORM`, `SYSTEM`, `CUSTOM`) and update `AgentProfile.origin`.
- [x] **Task 1.3** `[REQ-RECON-001]`: [GREEN] Add migration in `src/infrastructure/memory/connection.py` adding `origin TEXT NOT NULL DEFAULT 'custom'` to `custom_agents` and `agent_overrides` tables.
- [x] **Task 1.4** `[REQ-RECON-001]`: [GREEN] Update `src/infrastructure/memory/repositories/settings.py` to persist and load `origin`.

### Slice 2: Declarative Pack Reconciler
- [x] **Task 2.1** `[REQ-RECON-002, REQ-RECON-003]`: [RED] Write unit tests in `tests/unit/skills/test_declarative_pack_reconciler.py` verifying desired-state reconciliation, platform seed purging, and custom agent preservation.
- [x] **Task 2.2** `[REQ-RECON-002]`: [GREEN] Implement `DeclarativePackReconciler` in `src/infrastructure/skills/reconciler.py`.
- [x] **Task 2.3** `[REQ-RECON-004]`: [GREEN] Hook reconciler into `BuiltinAgentRegistry.bootstrap()` and `install_platform_agent_packs()` before tool mounting.
- [x] **Task 2.4** `[REQ-RECON-004]`: [GREEN] Update pack discovery loop in `install_platform_agent_packs()` to ignore unmanaged packs.

### Slice 3: API Origin Surfacing & UI Badging
- [x] **Task 3.1** `[REQ-RECON-005]`: [RED] Write API test in `tests/unit/web/test_agent_origin_api.py` verifying `/api/agents` returns `origin` and `DELETE /api/agents/{id}` forbids deleting platform agents.
- [x] **Task 3.2** `[REQ-RECON-005]`: [GREEN] Update `src/web/routers/agents.py` `_public_agent()` and `delete_agent()`.
- [x] **Task 3.3** `[REQ-RECON-005]`: [GREEN] Update Agent Studio UI in `src/web/static/modules/studios/forge.js` to render badge based on `origin`.

### Slice 4: Verification, RTM, & Pre-flight
- [x] **Task 4.1**: Run full test suite and linters (`pytest`, `ruff`, `vitest`).
- [x] **Task 4.2**: Register requirements `[REQ-RECON-001..005]` in `docs/rtm.json`.
- [x] **Task 4.3**: Run `python .agents/skills/rtm-sync/scripts/preflight.py` ensuring 100% green gate.
- [x] **Task 4.4**: Update `CHANGELOG.md` `[Unreleased]`.
