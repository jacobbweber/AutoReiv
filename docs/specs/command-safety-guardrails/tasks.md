# Task Breakdown: Dangerous Shell Command Safety Guardrails & Path Traversal Protection

> **Spec Status**: Implemented  
> **Target Release**: Milestone 13 (v0.13.0)  
> **Card Reference**: [CARD-045](file:///.github/cards/CARD-045-dangerous-shell-command-safety-guardrails-and-path-traversal-protection.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/command-safety-guardrails/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/command-safety-guardrails/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Domain Safety Models & Guardrail Engine
- [x] **Task 1.1**: Create `src/domain/safety/models.py` with `RiskLevel`, `SafetyViolation`, and `CommandSafetyReport` (`[REQ-GUARD-001]`).
- [x] **Task 1.2**: Implement `src/application/safety/command_guardrail.py` with regex & heuristic pattern matching for destructive commands, fork bombs, remote pipe execution, and path traversal (`[REQ-GUARD-002]`, `[REQ-GUARD-003]`).

### Slice 2: Subprocess & Sandbox Integration
- [x] **Task 2.1**: Integrate `CommandGuardrail.evaluate` into `src/application/skills/sandbox_worker.py` and `sandbox_skill.py` (`[REQ-GUARD-002]`).

### Slice 3: Verification, Pre-Flight & Gate Closure
- [x] **Task 3.1**: Author unit and integration tests in `tests/unit/safety/test_command_guardrail.py` (`[REQ-GUARD-004]`).
- [x] **Task 3.2**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-GUARD-004]`).
- [x] **Task 3.3**: Author ADR-0045 and sync `docs/rtm.json` with `[REQ-GUARD-001]` through `[REQ-GUARD-004]`.
- [x] **Task 3.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.


