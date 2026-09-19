# [CARD-363] Mechanical Capability Linter & Contract Compiler

> **Status**: Scaffold Ready  
> **Created**: 2026-09-19  
> **Spec Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [docs/specs/capability-linter/](file:///d:/Projects/Active/AutoReiv/docs/specs/capability-linter/)  
> **Labels**: `type:feature`, `domain:capabilities`, `domain:skills`, `architecture:autonomic-os`

---

## 1. Why / Intent

As established in **ADR-0054**, intelligence in an autonomic operating system resides in foundational parametric weights, while execution is governed by **Tools (Syscalls)** and **Skills (Procedural Runbooks)**. Previously, `SKILL.md` runbooks were treated as passive markdown documentation with informal tool lists and unverified completion criteria. This allowed tool bloat to accumulate unchecked, degrading local model attention and violating the Rule of 7.

AutoReiv requires a **Mechanical Capability Linter & Contract Compiler** that compiles `SKILL.md` files into structured, typed capability contracts and mechanically validates them against the 5 God-Agent thresholds before they enter runtime execution or get promoted into production packs.

---

## 2. What to Build

1. **Skill Contract Domain Models (`src/domain/skills/contract.py`)**:
   - `SkillContract`: Typed Pydantic v2 model representing compiled skills with `name`, `description`, `version`, `requires_tools`, `verification`, and `safety`.
   - `VerificationContract`: Explicit completion contract defining `kind` (`command`, `exit_code`, `assertion`, `file_exists`, `checker`) and testable rule criteria.
   - `SafetyContract`: Security boundaries (`read_only`, `requires_hitl`, `untrusted_input_allowed`).
   - `LintViolation` and `LintReport`: Diagnostic report structures with rule codes and severity.

2. **Mechanical Capability Compiler & Linter (`src/application/skills/linter.py`)**:
   - `SkillContractCompiler`: Compiles raw markdown and frontmatter, evaluates rules `CAP-001` (tool cap <= 6), `CAP-002` (mandatory verification), `CAP-003` (security boundary collision), and `CAP-004` (runbook size budget).
   - `CapabilityLinter`: File and directory scanner across platform packs (`platform-packs/`) and user data packs (`$DATA_DIR/packs/`, `$DATA_DIR/skills/`).

3. **CLI Command (`src/cli/main.py`)**:
   - `autoreiv lint-skills [PATH...] [--json]`: Scans capability directories, prints human-readable or JSON reports, and exits with code 0 on clean pass or code 1 on errors.

4. **REST API Endpoint (`src/web/routers/skills.py`)**:
   - `POST /api/skills/lint`: Real-time contract validation for raw content or file paths in Agent Forge.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] **[REQ-CAP-LINT-001]**: `SkillContractCompiler` enforces `len(requires_tools) <= 6` (Rule `CAP-001`), rejecting skills with > 6 tools.
- [ ] **[REQ-CAP-LINT-002]**: Every skill contract requires a deterministic verification contract or testable `## Done-when` section (Rule `CAP-002`).
- [ ] **[REQ-CAP-LINT-003]**: Forbids untrusted external inputs from co-mingling with mutating host levers without explicit HITL approval (Rule `CAP-003`).
- [ ] **[REQ-CAP-LINT-004]**: CLI subcommand `autoreiv lint-skills` scans target directories, returning exit code 0 or 1 with formatted diagnostics.
- [ ] **[REQ-CAP-LINT-005]**: REST API endpoint `POST /api/skills/lint` returns structured validation results.
- [ ] All platform seed skills in `platform-packs/` pass the linter with zero errors.
- [ ] Automated tests green via `pytest tests/unit/skills/test_capability_linter.py`.
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Invariants

- Grounded in **ADR-0054** (Section 4.5 Mechanical Governance).
- Follow strict Red-Green-Refactor TDD on branch `feat/card-363-capability-linter`.
- Platform seed packs (`platform-packs/`) must remain 100% compliant with the linter.
- Wait for Jacob's explicit **build** before implementing code.
