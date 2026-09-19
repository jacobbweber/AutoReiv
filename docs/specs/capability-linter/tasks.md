# Vertical Slice Tasks: Mechanical Capability Linter & Contract Compiler

> **Spec Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/capability-linter/requirements.md)  
> **Card Reference**: [CARD-363](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-363-mechanical-capability-linter-contract-compiler.md)

---

## Slice 1: Skill Contract Domain & Mechanical Compiler (`[REQ-CAP-LINT-001]`, `[REQ-CAP-LINT-002]`, `[REQ-CAP-LINT-003]`)

- [ ] **Task 1.1** `[REQ-CAP-LINT-001]`, `[REQ-CAP-LINT-002]`, `[REQ-CAP-LINT-003]`: [RED] Write unit tests in `tests/unit/skills/test_capability_linter.py` asserting `CAP-001` (tool budget <= 6), `CAP-002` (mandatory verification contract), and `CAP-003` (security boundary collision).
- [ ] **Task 1.2** `[REQ-CAP-LINT-001]`: [GREEN] Implement domain models in `src/domain/skills/contract.py` (`SkillContract`, `VerificationContract`, `SafetyContract`, `LintViolation`, `LintReport`).
- [ ] **Task 1.3** `[REQ-CAP-LINT-001]`, `[REQ-CAP-LINT-002]`, `[REQ-CAP-LINT-003]`: [GREEN] Implement `SkillContractCompiler` and `CapabilityLinter` in `src/application/skills/linter.py`.
- [ ] **Task 1.4**: [REFACTOR] Ensure existing seed `SKILL.md` files under `platform-packs/` conform to the linter without violations.

---

## Slice 2: CLI Command & REST API Integration (`[REQ-CAP-LINT-004]`, `[REQ-CAP-LINT-005]`)

- [ ] **Task 2.1** `[REQ-CAP-LINT-004]`, `[REQ-CAP-LINT-005]`: [RED] Write tests for CLI execution (`autoreiv lint-skills`) and REST endpoint (`POST /api/skills/lint`).
- [ ] **Task 2.2** `[REQ-CAP-LINT-004]`: [GREEN] Implement `autoreiv lint-skills` subcommand in `src/cli/main.py`.
- [ ] **Task 2.3** `[REQ-CAP-LINT-005]`: [GREEN] Implement `POST /api/skills/lint` endpoint in `src/web/routers/skills.py`.

---

## Slice 3: Verification & Preflight Gates

- [ ] **Task 3.1**: Run `pytest tests/unit/skills/test_capability_linter.py` and full unit test suite.
- [ ] **Task 3.2**: Run `autoreiv lint-skills platform-packs/` to verify zero seed pack violations.
- [ ] **Task 3.3**: Run `ruff check src/ tests/` and `npm run lint:frontend`.
- [ ] **Task 3.4**: Sync `docs/rtm.json` with requirements `[REQ-CAP-LINT-001]` through `[REQ-CAP-LINT-005]`.
- [ ] **Task 3.5**: Update `CHANGELOG.md` under `[Unreleased]`.
