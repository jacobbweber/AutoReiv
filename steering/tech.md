# Technical Steering & Environment Standards

> **Purpose**: Documents the technology stack, runtime constraints, security boundaries, and command-line execution standards for AI agents in this repository.

---

## 1. Technology Stack

### Backend Stack

- **Language / Runtime**: Python 3.12+
- **Framework**: FastAPI with Starlette TestClient
- **Package Manager**: Astral UV / pip
- **Database & Persistence**: SQLite (in-memory test mode; user-data root `%LOCALAPPDATA%\AutoReiv\autoreiv.db` in production)
- **Validation**: Pydantic v2
- **Linter & Formatter**: Ruff (`ruff check .`, `ruff format .`)
- **Test Runner**: Pytest (`pytest -q`)

### Frontend Stack

- **Architecture**: Zero-Build Native ES Modules (`src/web/static/modules/`)
- **Styling & UI**: Tailwind CSS (CDN), Lucide Icons, Mermaid.js
- **State Management**: Reactive `createStore` factory (`src/web/static/modules/state/store.js`)
- **Linter & Formatter**: ESLint 9 (Flat Config `eslint.config.js`), Prettier (`.prettierrc`)
- **Unit Test Runner**: Vitest (`npm run test:unit:frontend`)
- **End-to-End Smoke Runner**: Playwright (`npm run test:smoke`)

---

## 2. Standard Execution Commands

Agents MUST use these standardized commands during development and verification cycles:

```bash
# Unified Pre-Flight Gate (Ruff -> Pytest -> Honesty Smoke -> ESLint -> Vitest -> Playwright)
npm run preflight

# Python Verification
pytest -q
ruff check .
ruff format .

# Frontend Verification
npm run lint:frontend
npm run format:frontend
npm run test:unit:frontend
npm run test:smoke
```

---

## 3. Security & Operational Constraints

1. **No Hardcoded Secrets**: All credentials, tokens, and keys must be injected via environment variables or stored securely in SQLite with UI response masking.
2. **Deterministic Outputs**: Ensure random seeds or mock fixtures are used in tests to avoid flaky test results.
3. **Hermetic Testing**: Unit and integration tests must not attempt outbound network calls or modify production databases or vaults.
4. **Session Hygiene**: Always operate on isolated `feat/*` branches cut from `qa`, concluding sessions once PR and DoD gates pass.

Operator serve restart (coding assistants): see `.agents/skills/serve-hygiene/SKILL.md`.
