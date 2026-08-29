# [CARD-086] SDD Project Scaffold

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/sdd-project-scaffold/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
New coding projects should start with a Kiro-style SDD skeleton so cards, specs, TDD, and conventional commits are already there. Language-agnostic.

## 2. What to Build
- In-repo template `templates/sdlc-project/` with AGENTS.md, docs/specs, .github/cards, CHANGELOG, VERSION 0.1.0, CONTRIBUTING, tests, README.
- `create_project` (tool + studio API) copies the template into `projects_root/<slug>`.
- Jail: no escape from projects_root.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-050]`: create_project materializes the template files under the root.
- [x] `[REQ-SDLC-053]`: Path escapes are denied. Tool is registered. HITL on create_project.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Language-agnostic. Do not invent a second HITL engine.
- Do not add create_project to Conductor's locked 11-tool allowlist.
- Do not push. Stay on `qa`.
