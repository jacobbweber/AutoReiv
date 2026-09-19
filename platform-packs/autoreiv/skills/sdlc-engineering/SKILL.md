---
name: Software Engineering & TDD (SDLC)
description: Full-lifecycle software engineering including read-only exploration, TDD implementation, ADR/spec authoring, multi-language test execution, and self-correction.
version: 1.0.0
tier: platform
requires_tools:
  - read_project_file
  - write_project_file
  - list_project_dir
  - cli_exec
  - execute_code
  - propose_followup
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: All targeted unit, integration, and linter checks pass with zero regressions.
---

# Software Engineering & TDD (SDLC)

Execute structured software engineering across the active project directory selected in Projects Studio. You follow an iterative, test-driven development loop, keep architectural decisions documented, and self-correct on failure before reporting completion.

## Core Protocols

1. **Read-Only Exploration First**:
   - Inspect existing project structure using `list_project_dir` and `read_project_file`.
   - Never write code blind. Understand project patterns, dependencies, and interfaces before proposing changes.

2. **Specification & Architectural Integrity**:
   - Keep architectural decisions documented in ADRs under `docs/adr/`.
   - Author formal specifications under `docs/specs/` following Spec-Driven Development (SDD) standards.
   - Use `propose_followup` when new work items or edge cases are uncovered.

3. **Test-Driven Development (TDD)**:
   - Follow strict Red-Green-Refactor cycles.
   - Write failing unit or integration tests before implementing production changes using `write_project_file`.
   - Verify code behavior iteratively.

4. **Multi-Language Verification & Self-Correction**:
   - Run automated test suites and linters via `cli_exec` or `execute_code` (PowerShell, Python, TypeScript).
   - If tests fail, inspect the stdout/stderr, trace the failure to its root cause, and self-correct before reporting completion.
   - Never claim tests passed without executing verification.

## Done-when

- Target code and tests are implemented following strict TDD.
- Automated tests and linters execute via `cli_exec` or `execute_code` and exit with code 0.
- All modified code adheres to project architectural constraints and linting rules.
