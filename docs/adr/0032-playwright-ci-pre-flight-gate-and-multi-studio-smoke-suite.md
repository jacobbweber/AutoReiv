# ADR-0032: Playwright CI Pre-Flight Gate and Multi-Studio Smoke Suite

## Context and Problem Statement
With the frontend modularization completed in CARD-031, AutoReiv required continuous automated proof across its polyglot stack (Python FastAPI backend, native ES modules frontend, SQLite WAL persistence). Previously, developers and agents had to run disparate commands manually before creating pull requests, and GitHub PRs lacked an automated continuous integration runner to catch regressions.

## Decision Drivers
- **Deterministic Multi-Studio Coverage**: Validate all 7 studios (Chat, Routines, Observability, Agent Forge, Settings, System Manual, Wiki Vault) under real headless Chromium browser execution.
- **Zero-Friction Single-Command Pre-Flight**: Provide a unified CLI runner (`npm run preflight`) that validates the entire Definition of Done locally in under 30 seconds.
- **Automated CI Workflow**: Establish a GitHub Actions pipeline (`.github/workflows/ci.yml`) triggered on PRs and pushes to `main` and `qa`.

## Considered Options
1. **Option 1**: Manual developer verification before each PR.
2. **Option 2 (Accepted)**: GitHub Actions CI with Astral `uv` caching, unified `preflight.py` runner, and deep multi-studio Playwright smoke assertions.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Every commit to `qa` and `main` is automatically tested across Ruff, Pytest, Vitest, Playwright, and RTM.
- Local pre-flight gate (`npm run preflight`) catches all failures in a single command before pushing.
- Failure diagnostics (traces and screenshots) are automatically retained in `test-results/` and uploaded as GitHub Actions artifacts on failure.

### Negative Consequences / Trade-offs
- CI builds require downloading Chromium binaries via Playwright (mitigated by Node and UV layer caching).
