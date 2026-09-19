# Requirements Specification: Mechanical Capability Linter & Contract Compiler

> **Spec Status**: Approved (Draft for Review)  
> **Target Release**: v0.18.0 (Milestone 18 — Autonomic OS & Mechanical Governance)  
> **Primary Components**: `SkillContractCompiler` (`src/application/skills/linter.py`), `SkillContract` (`src/domain/skills/contract.py`), CLI Dispatcher (`src/cli/main.py`), and REST Router (`src/web/routers/skills.py`)  
> **Grounding**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [CARD-363](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-363-mechanical-capability-linter-contract-compiler.md)

---

## 1. Executive Summary & Intent

Per **ADR-0054**, intelligence in an autonomic operating system resides in foundational parametric weights, while execution is governed by **Tools (Syscalls)** and **Skills (Procedural Runbooks)**. Previously, `SKILL.md` runbooks were treated as passive markdown documentation with informal tool lists and unverified completion criteria. This allowed tool bloat to accumulate unchecked, degrading local model attention and violating the Rule of 7.

**CARD-363** establishes the **Mechanical Capability Linter & Contract Compiler**:
1. Transforms `SKILL.md` into a typed, compiled **Skill Contract** with structured YAML frontmatter.
2. Enforces mechanical governance rules:
   - **`CAP-001` (Tool Cap)**: No skill may declare more than 6 tools (`len(requires_tools) <= 6`).
   - **`CAP-002` (Verification Contract)**: Mandatory testable completion verification criteria (command, test target, file check, or assertion pattern) instead of conversational vibes.
   - **`CAP-003` (Security Boundary)**: Untrusted external inputs cannot co-mingle with mutating host levers (`cli_exec`, `write_project_file`, `db_drop`) without explicit HITL gating.
   - **`CAP-004` (Runbook Size Cap)**: Markdown runbook body must remain under 8,000 characters (< 2,000 tokens) to protect pre-fill context.
3. Provides an automated CLI command (`autoreiv lint-skills`), REST API (`POST /api/skills/lint`), and Preflight verification integration.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-CAP-LINT-001]: Tool Entropy Ceiling Enforcement (Rule CAP-001)
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL reject any skill contract declaring more than 6 required tools (len(requires_tools) <= 6) to preserve headroom for baseline platform coordination primitives under the Rule of 7 entropy budget.`
- **Acceptance Criteria**:
  - [ ] Given a `SKILL.md` with 7 or more tools declared in `requires_tools`, the compiler emits violation `CAP-001` with severity `ERROR`.
  - [ ] Given a `SKILL.md` with 1 to 6 tools declared in `requires_tools`, the compiler passes rule `CAP-001`.
  - [ ] Legacy skills lacking explicit `requires_tools` fall back to scanning tool names mentioned in `## Available Tools` or markdown body, and apply the same 6-tool ceiling.

### [REQ-CAP-LINT-002]: Mandatory Completion Verification Contract (Rule CAP-002)
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL require every skill contract to define a deterministic verification clause specifying check kind and testable rule criteria, rejecting unverified or vibes-only skills.`
- **Acceptance Criteria**:
  - [ ] A skill contract must contain either a structured `verification` frontmatter object (specifying `kind: command|exit_code|assertion|file_exists` and `rule`), or a markdown `## Done-when` / `## Verification` section containing a non-empty testable rule.
  - [ ] Skills lacking verification definitions emit violation `CAP-002` with severity `ERROR`.

### [REQ-CAP-LINT-003]: Security Boundary Collision Guard (Rule CAP-003)
- **Type**: State-Driven
- **EARS Statement**: `WHILE a skill contract permits untrusted external inputs (untrusted_input_allowed=true), THE SYSTEM SHALL forbid high-risk mutating host tools unless explicitly marked for HITL approval or sandboxed isolation.`
- **Acceptance Criteria**:
  - [ ] If `untrusted_input_allowed: true` and any tool in `requires_tools` is high-risk (`cli_exec`, `write_project_file`, `repo_file_write`, `execute_code`, `execute_agent_database`) without `requires_hitl: true`, the compiler emits violation `CAP-003` with severity `ERROR`.

### [REQ-CAP-LINT-004]: CLI Command `autoreiv lint-skills`
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator invokes 'autoreiv lint-skills [PATH...]', THE SYSTEM SHALL scan target directories (defaulting to platform packs and user data packs), evaluate all SKILL.md runbooks against rules CAP-001 through CAP-004, and exit with code 0 on success or code 1 on errors.`
- **Acceptance Criteria**:
  - [ ] Running `autoreiv lint-skills` prints a formatted human-readable summary of scanned skills, violation counts, and details per skill.
  - [ ] Running `autoreiv lint-skills --json` outputs a clean JSON report conforming to `LintReport`.
  - [ ] Exits with code 1 if any `ERROR` violation is detected; exits with code 0 if all skills are compliant.

### [REQ-CAP-LINT-005]: REST API Endpoint `POST /api/skills/lint`
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a client sends a POST request to '/api/skills/lint' with raw SKILL.md text or a file path, THE SYSTEM SHALL compile the contract and return structured validation results.`
- **Acceptance Criteria**:
  - [ ] Request body accepts `{"content": "<markdown>", "path": "<optional_path>"}`.
  - [ ] Response includes `{"valid": bool, "contract": {...}, "violations": [{"rule": "...", "severity": "...", "message": "..."}]}`.

---

## 3. Boundary & Non-Functional Constraints

- **Zero Breaking Seeds**: All platform seed packs under `platform-packs/` must pass the mechanical linter cleanly.
- **Fast Execution**: Compiling and linting 20 skills must complete in under 50ms (sub-millisecond per skill).
- **Graceful Fallback**: Missing frontmatter gracefully falls back to parsing markdown headings (`## Name`, `## Available Tools`, `## Done-when`).
