# Vertical Slices & Task Decomposition: In-App Software Updates and Upstream Repository Sync

> **Spec Status**: Approved  
> **Target Release**: CARD-196  
> **Primary Component**: AutoReiv.System & AutoReiv.SettingsStudio

---

## Vertical Slices

### Slice 1: Domain Models and Update Service Core (TDD)
- [ ] Task 1.1: [REQ-UPD-001] Define `SystemVersionInfo`, `UpdateConfig`, `UpdateCheckResult`, `UpdateApplyResult` in `src/domain/system/models.py`.
- [ ] Task 1.2: [REQ-UPD-001] Implement Red tests in `tests/unit/system/test_update_service.py` for version inspection, git status detection, and deployment mode resolution.
- [ ] Task 1.3: [REQ-UPD-002, REQ-UPD-003] Implement Red tests for config persistence and upstream update check logic with mock remotes/GitHub API.
- [ ] Task 1.4: [REQ-UPD-004, REQ-UPD-005] Implement Red tests for dirty tree guard, database snapshotting, and fast-forward pull execution.
- [ ] Task 1.5: Implement `UpdateService` in `src/application/system/update_service.py` to turn tests Green.

### Slice 2: Web Router & API Contract Integration
- [ ] Task 2.1: [REQ-UPD-001..005] Implement Red integration tests in `tests/unit/web/test_system_updates_router.py`.
- [ ] Task 2.2: Mount `GET /api/system/version`, `GET/PUT /api/system/updates/config`, `GET /api/system/updates/check`, and `POST /api/system/updates/apply` in `src/web/routers/system.py`.
- [ ] Task 2.3: Dynamic version resolution in `/health` and `/api/health`.

### Slice 3: Settings Studio Frontend Surface
- [ ] Task 3.1: [REQ-UPD-001, REQ-UPD-002] Add "System & Software Updates" panel markup in `src/web/templates/index.html`.
- [ ] Task 3.2: [REQ-UPD-003, REQ-UPD-004] Implement client-side controller logic in `src/web/static/modules/studios/settings.js` for version badge hydration, repo config save, update check, and safe update apply with confirmation modal.
- [ ] Task 3.3: Write Vitest frontend unit tests in `tests/unit/frontend/system_updates.test.js`.

### Slice 4: DoD Pre-flight, RTM Sync, and QA Promotion
- [ ] Task 4.1: Update `docs/rtm.json` with `[REQ-UPD-001]` through `[REQ-UPD-005]`.
- [ ] Task 4.2: Run `ruff`, `eslint`, `vitest`, `playwright`, `pytest`, and `verify_rtm.py`.
- [ ] Task 4.3: Update `CHANGELOG.md` and `.github/cards/CARD-196-in-app-software-updates-and-upstream-repository-sync.md`.
