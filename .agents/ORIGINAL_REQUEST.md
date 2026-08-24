# Original User Request

## 2026-08-24T01:42:47Z

<USER_REQUEST>
Perform a comprehensive code audit, root-cause analysis, and targeted bug-fix pass on the AutoReiv codebase — an autonomous AI agent control plane built with Python (FastAPI/Uvicorn backend, SQLite via autoreiv.db) and a browser-based UI (single-page `index.html` + `app.js`). The codebase has accumulated UI regressions and logic defects from rapid iterative development across many long sessions. The team must read source files in full, trace execution paths, identify confirmed defects, apply targeted fixes, and validate with the existing test suite.

Working directory: d:\Projects\Active\AutoReiv
Integrity mode: demo

---

## Context

The application has experienced:
- UI elements (buttons, drawers, modals, pickers) not rendering or not responding
- Documents and content not rendering where expected
- Navigation / routing breakdowns
- Suspected state management issues and stale/incorrect logic introduced by context rot across long AI-pair-programming sessions
- Possible mismatches between the Python backend (`src/web/app.py`, ~48KB) and the frontend (`src/web/static/app.js`, ~160KB; `src/web/templates/index.html`, ~93KB)

The domain layer lives under `src/domain/` (agents, gateway, kernel, memory, observability, orchestration, planning, routines, settings, skills, telemetry, wiki). The application layer is under `src/application/`. Infrastructure is under `src/infrastructure/`. Tests are under `tests/unit/` and `tests/integration/`. Dev tooling: `ruff` for linting, `mypy` for type checking, `pytest` for tests.

---

## Requirements

### R1. Full Static + Structural Analysis
Read every file in `src/` and `tests/` in full. Identify:
- Ruff lint violations and mypy type errors
- Circular imports or broken module references
- Dead code, orphaned routes, and unused symbols
- Inconsistencies between backend route definitions in `src/web/app.py` and API calls made in `src/web/static/app.js`

### R2. UI / Frontend Trace and Regression Root-Cause
Trace all UI interactions in `index.html` and `app.js` end-to-end:
- For every button, drawer, modal, picker, and list component: verify the event handler exists, is correctly wired, and calls a valid backend endpoint or performs the correct in-memory operation
- Identify any component that fails to render, renders empty, or triggers a silent error
- Identify any DOM element reference (`getElementById`, `querySelector`, class/ID selectors) that does not match a corresponding element in `index.html`
- Check all conditional rendering logic for off-by-one errors, wrong truthy checks, or stale state assumptions

### R3. Backend Logic Audit
In `src/web/app.py` and all `src/domain/**` and `src/application/**` modules:
- Verify all FastAPI route handlers return correct HTTP status codes and response schemas
- Check all database interactions (SQLite via `autoreiv.db`) for missing commits, incorrect queries, or unhandled exceptions
- Validate that LLM provider integration (Ollama and any cloud providers) correctly handles connection errors, empty responses, and retries
- Flag any async/await misuse (missing `await`, sync blocking inside async context)

### R4. Test Coverage Verification and Gap Analysis
Run the existing test suite (`pytest tests/`) and report results. Identify:
- Tests that are currently failing and their root cause
- Gaps where confirmed bugs in R1–R3 have no test coverage
- Write targeted new tests for each confirmed bug before applying the fix (Red phase)

### R5. Targeted Bug Fixes and Validation
For each confirmed defect found in R1–R4:
- Apply the minimal fix required (KISS/YAGNI)
- Re-run `pytest tests/` and `ruff check src/` and `mypy src/` to confirm green status
- Do not refactor unrelated code; do not introduce speculative features

---

## Acceptance Criteria

### Static Analysis Clean
- [ ] `ruff check src/` exits with zero errors after fixes are applied
- [ ] `mypy src/ --ignore-missing-imports` exits with zero errors after fixes are applied

### Test Suite
- [ ] `pytest tests/ -v` passes with zero failures after fixes are applied
- [ ] At least one new test is added per confirmed backend or domain bug that had no existing coverage

### UI Regression Report
- [ ] A written audit report (`docs/audit/audit_report.md`) is produced listing every identified UI defect with: symptom, root cause, file + line reference, and resolution applied (or "deferred" with justification)
- [ ] Every button, drawer, modal, and picker in `index.html` is accounted for in the report — either confirmed working or confirmed fixed

### Backend Correctness
- [ ] All FastAPI route handlers referenced in `app.js` exist in `app.py` with matching HTTP method and path
- [ ] No unhandled exceptions in async route handlers (all wrapped with proper error responses)
- [ ] All `await` expressions verified as applied to actual coroutines

### No Regressions
- [ ] The full test suite that was passing before this audit still passes after all changes

---

## Verification Resources

- Existing test suite: `tests/unit/` and `tests/integration/`
- Lint config: `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`)
- Test runner config: `pyproject.toml` (`[tool.pytest.ini_options]`)
- Run tests: `pytest tests/ -v`
- Run lint: `ruff check src/`
- Run type check: `mypy src/ --ignore-missing-imports`
</USER_REQUEST>
