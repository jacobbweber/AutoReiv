# Requirements Specification: Dangerous Shell Command Safety Guardrails & Path Traversal Protection

> **Spec Status**: Approved  
> **Target Release**: Milestone 13 (v0.13.0)  
> **Card Reference**: [CARD-045](file:///.github/cards/CARD-045-dangerous-shell-command-safety-guardrails-and-path-traversal-protection.md)  

> **Primary Component**: AutoReiv Safety (`src/domain/safety/models.py`, `src/application/safety/command_guardrail.py`, `src/application/skills/sandbox_worker.py`)

---

## 1. Executive Summary & Intent

**CARD-045** provides deterministic safety guardrail evaluation for shell commands and script executions, blocking destructive operations (recursive deletions, disk wipes, fork bombs, remote pipe execution) and path traversal outside allowed workspaces.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-GUARD-001] Domain Safety Risk Models & Violations
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** define `RiskLevel` (`SAFE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), `SafetyViolation`, and `CommandSafetyReport` domain models capturing rule ID, risk level, explanation, and matched pattern.

### [REQ-GUARD-002] Deterministic Command Guardrail Engine
- **EARS Pattern**: Event-Driven
- **Requirement**: When a command string is evaluated, the `CommandGuardrail` engine **shall** inspect for destructive operations (`rm -rf /`, `mkfs`, `format`, `dd`, `shutdown`), fork bombs, remote pipe-to-shell payloads (`curl | sh`), and system directory modifications, returning a `CommandSafetyReport`.

### [REQ-GUARD-003] Workspace Path Traversal Protection
- **EARS Pattern**: Event-Driven
- **Requirement**: When file paths or command arguments are evaluated, the `CommandGuardrail` **shall** detect and block traversal sequences (`../`, `/etc/`, `C:\Windows\`) attempting to escape the authorized workspace directory.

### [REQ-GUARD-004] Comprehensive Safety Guardrails Unit Test Suite
- **EARS Pattern**: State-Driven
- **Requirement**: When running `pytest`, the test runner **shall** verify detection of dangerous commands, path traversal attempts, allowlisted safe commands, and integration with `SandboxedSubprocessWorker` with 100% passing tests.


---

## 3. Acceptance Criteria

- [ ] `AC-1`: Commands containing destructive root wipes (`rm -rf /`, `rmdir /s /q C:\`) receive `CRITICAL` risk and `is_safe = False`.
- [ ] `AC-2`: Piped remote execution (`curl http://... | bash`) is identified as `CRITICAL` risk.
- [ ] `AC-3`: Paths escaping root or targeting sensitive OS directories (`/etc/shadow`, `C:\Windows\System32`) are blocked.
- [ ] `AC-4`: Normal developer commands (`pytest`, `npm test`, `git status`, `python app.py`) evaluate as `SAFE` (`is_safe = True`).
- [ ] `AC-5`: `SandboxedSubprocessWorker` aborts execution if command violates safety guardrails.
- [ ] `AC-6`: `npm run preflight` passes all 6 quality gates cleanly.
