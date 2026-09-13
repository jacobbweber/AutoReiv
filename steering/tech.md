# Technical Steering & Environment Standards

> **Purpose**: Documents the technology stack, runtime constraints, security boundaries, and command-line execution standards for AI agents in this repository.

---

## 1. Technology Stack

### Backend Stack
- **Language / Runtime**: Python 3.12+
- **Framework**: FastAPI with Starlette TestClient
- **Package Manager**: Astral UV / pip
- **Database & Persistence**: SQLite (in-memory test mode, `./data/autoreiv.db` production)
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

Agents MUST use these standardized commands during TDD and verification cycles:

```bash
# Unified 6-Stage Pre-Flight Gate (Ruff -> Pytest -> ESLint -> Vitest -> Playwright -> RTM)
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

# Traceability & Blast Radius Verification
python .agents/skills/rtm-sync/scripts/verify_rtm.py
python .agents/skills/rtm-sync/scripts/verify_rtm.py --impact <file_path>
```

---

## 3. Security & Operational Constraints
1. **No Hardcoded Secrets**: All credentials, tokens, and keys must be injected via environment variables or stored securely in SQLite with UI response masking.
2. **Deterministic Outputs**: Ensure random seeds or mock fixtures are used in tests to avoid flaky test results.
3. **Hermetic Testing**: Unit and integration tests must not attempt outbound network calls or modify production databases or vaults.
4. **Session Hygiene**: Always operate on isolated `feat/*` branches cut from `qa`, concluding sessions once PR and DoD gates pass.

---

## 4. Serve / orphan hygiene (Jarvis)

Exactly **one** AutoReiv serve on `:8000` from the **current branch tip**, with versioned SPA chrome (`app.js?v=`). Prevents stale-orphan false fails during live smoke.

```powershell
uv run python scripts/restart_serve.py --status
uv run python scripts/restart_serve.py --dry-run
uv run python scripts/restart_serve.py --port 8000 --host 127.0.0.1
.\scripts\restart_serve.ps1
```

Helper prints: `branch`, tip SHA, `app.js?v=` (from `src/web/templates/index.html`), port, orphans killed, started.

After restart: browser **Ctrl+F5**; confirm Network shows matching `app.js?v=`; confirm the git checkout has **no** new live `*.db` / `packs/` (user data only under `%LOCALAPPDATA%\AutoReiv\`).

Script source of truth: `scripts/restart_serve.py` (CARD-256).

