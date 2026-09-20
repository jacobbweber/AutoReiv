---
id: CARD-385
title: "Dead Code, Orphaned Shims, and Linter Scavenger Pass"
status: In Review
created: 2026-09-20
adr: none
labels:
  - type:refactor
  - clean-up
  - domain:backend
  - domain:web
---

# [CARD-385] Dead Code, Orphaned Shims, and Linter Scavenger Pass

> **Status**: In Review  
> **Created**: 2026-09-20  
> **Labels**: `type:refactor`, `clean-up`, `domain:backend`, `domain:web`  
> **Branch**: `feat/card-385-dead-code-orphaned-shims-scavenger` off `qa`  
> **Reply to build**: **build** or **build CARD-385**  

---

## 1. The Four Beats

### Beat 1: What Jacob Means
Conclude the 3-pass code hygiene plan by conducting a thorough scavenger pass to excise orphaned shim files, obsolete backward-compatibility aliases, and lingering bytecode artifacts. Ensure zero dead code paths, zero orphaned shims, and zero linter warnings remain across the entire codebase.

### Beat 2: What AutoReiv Does Now
1. **Orphaned Router Shims**:
   - `src/web/routers/_card313_import_data_dir_migrate.py`: A 2-line placeholder left over from CARD-313 with 0 callers anywhere in the repository.
   - `src/web/routers/factory.py`: A 5-line deprecated router shim from CARD-171 that simply re-exports `agent_training_factory.router`, with 0 callers in application code or tests (the application entrypoint `src/web/app.py` already imports directly from `agent_training_factory`).
2. **Orphaned Orchestration Compatibility Shim**:
   - `src/application/orchestration/factory_runner.py`: A 9-line compatibility shim from CARD-171 that aliases `FactoryRunner = FactoryOrchestrator`, with 0 callers in the codebase.
   - `src/application/agent_training_factory/orchestrator.py`: Maintains an orphaned export alias `FactoryRunner = FactoryOrchestrator` on line 198.
3. **Stale Bytecode**:
   - Stale `.pyc` files from retired historical scratch scripts remain in the root `__pycache__` directory.

### Beat 3: What Will Change
1. **Excise Orphaned Shims**:
   - Delete `src/web/routers/_card313_import_data_dir_migrate.py`.
   - Delete `src/web/routers/factory.py`.
   - Delete `src/application/orchestration/factory_runner.py`.
   - Prune `FactoryRunner = FactoryOrchestrator` alias from `src/application/agent_training_factory/orchestrator.py`.
2. **Negative Assertion Regression Guard**:
   - Author `tests/unit/core/test_dead_code_shims_scavenger_385.py` to assert that the excised shim files do not exist on disk, cannot be imported as modules, and that `orchestrator.py` does not expose `FactoryRunner`.
3. **Linter & Boundary Scavenger Pass**:
   - Clean stale root `__pycache__` bytecode.
   - Run `ruff check .`, `npm run lint:frontend`, and `boundary_check.py` to confirm zero defects or leaks.
4. **Full Test Suite Verification**:
   - Run the complete preflight test suite to confirm zero regressions.

### Beat 4: What Dies Today (The Prune List)
1. `src/web/routers/_card313_import_data_dir_migrate.py` (file deleted).
2. `src/web/routers/factory.py` (file deleted).
3. `src/application/orchestration/factory_runner.py` (file deleted).
4. `FactoryRunner = FactoryOrchestrator` alias in `src/application/agent_training_factory/orchestrator.py` (line 198).
5. Stale `.pyc` entries in root `__pycache__`.

---

## 2. Acceptance Criteria (EARS)

- [x] **[REQ-385-001] (Excise Data Dir Migrate Shim)**: THE CODEBASE SHALL delete `src/web/routers/_card313_import_data_dir_migrate.py` with zero residual references across the repository.
- [x] **[REQ-385-002] (Excise Factory Router Shim)**: THE CODEBASE SHALL delete `src/web/routers/factory.py`, with all factory routing unified under `src/web/routers/agent_training_factory.py`.
- [x] **[REQ-385-003] (Excise FactoryRunner Compatibility Shim)**: THE CODEBASE SHALL delete `src/application/orchestration/factory_runner.py` and prune `FactoryRunner` alias from `orchestrator.py`.
- [x] **[REQ-385-004] (Negative Assertion Regression Guard)**: Automated tests SHALL verify that none of the retired shim files exist on the filesystem or can be imported into Python runtime space.
- [x] **[REQ-385-005] (Clean Linters and Boundary)**: `ruff check .` SHALL pass with 0 errors, `npm run lint:frontend` SHALL pass with 0 errors/warnings, and `boundary_check.py` SHALL report 0 leaks.
- [x] **[REQ-385-006] (Zero Regression)**: All existing unit, integration, and smoke test suites SHALL pass 100% green.

---

## 3. Constraints & Verification Plan

- Isolated feature branch: `feat/card-385-dead-code-orphaned-shims-scavenger` cut from `qa`.
- Subtractive engineering: strictly prune obsolete files and dead compatibility aliases.
- Pass `python .agents/skills/preflight/scripts/preflight.py` before In Review.
