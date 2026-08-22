# Technical Steering & Environment Standards

> **Purpose**: Documents the technology stack, runtime constraints, security boundaries, and command-line execution standards for AI agents in this repository.

---

## 1. Technology Stack
<!-- Customize for the specific repository instance -->
- **Language / Runtime**: Python 3.10+ / Node.js 20+ (Adaptable per project)
- **Primary Frameworks**: Clean Architecture / Ports & Adapters
- **Test Framework**: `pytest` / `vitest` / `jest`
- **Linter & Formatter**: `ruff` / `eslint` / `prettier`

---

## 2. Standard Execution Commands

Agents MUST use these standardized commands during TDD and verification cycles:

```bash
# Automated Test Suites
test_unit_cmd: pytest tests/unit
test_integration_cmd: pytest tests/integration
test_all_cmd: pytest

# Code Quality & Static Analysis
lint_cmd: ruff check .
format_check_cmd: ruff format --check .
typecheck_cmd: mypy .

# Traceability & Blast Radius Verification
rtm_verify_cmd: python .agents/skills/rtm-sync/scripts/verify_rtm.py
rtm_impact_cmd: python .agents/skills/rtm-sync/scripts/verify_rtm.py --impact <file_path>
```

---

## 3. Security & Operational Constraints
1. **No Hardcoded Secrets**: All credentials, tokens, and keys must be injected via environment variables or secret managers.
2. **Deterministic Outputs**: Ensure random seeds or mock fixtures are used in tests to avoid flaky test results.
3. **Hermetic Testing**: Unit tests must not attempt outbound network calls or modify production databases.
