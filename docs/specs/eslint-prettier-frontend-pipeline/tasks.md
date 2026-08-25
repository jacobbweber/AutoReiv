# Task Breakdown: ESLint & Prettier Static Analysis Pipeline for Frontend

> **Spec Status**: Implemented  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-034](file:///.github/cards/CARD-034-eslint-and-prettier-static-analysis-pipeline-for-frontend.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/eslint-prettier-frontend-pipeline/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/eslint-prettier-frontend-pipeline/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Linter & Formatter Tooling Installation & Config
- [x] **Task 1.1**: Install `eslint`, `@eslint/js`, `globals`, and `prettier` as devDependencies (`[REQ-LINT-001]`, `[REQ-LINT-002]`).
- [x] **Task 1.2**: Create `eslint.config.js` and `.prettierrc` with browser and node globals (`[REQ-LINT-001]`, `[REQ-LINT-002]`).
- [x] **Task 1.3**: Add `"lint:frontend"`, `"lint:frontend:fix"`, and `"format:frontend"` npm scripts to `package.json`.

### Slice 2: Codebase Sweep & Rule Compliance
- [x] **Task 2.1**: Run `npm run lint:frontend` and resolve any unused variables, missing globals, or formatting defects across `src/web/static/` and `tests/` (`[REQ-LINT-004]`).
- [x] **Task 2.2**: Verify `npm run lint:frontend` passes with zero errors and zero warnings.

### Slice 3: Pre-Flight & CI Integration
- [x] **Task 3.1**: Update `.agents/skills/rtm-sync/scripts/preflight.py` to include the Frontend Linter stage (`[REQ-LINT-003]`).
- [x] **Task 3.2**: Update `.github/workflows/ci.yml` to include `npm run lint:frontend` in the CI pipeline (`[REQ-LINT-003]`).

### Slice 4: Verification & Gate Closure
- [x] **Task 4.1**: Execute `npm run preflight` to verify all 6 gates pass 100%.
- [x] **Task 4.2**: Author ADR-0034 and sync `docs/rtm.json` with `[REQ-LINT-001]` through `[REQ-LINT-004]`.
- [x] **Task 4.3**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

