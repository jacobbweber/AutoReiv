# Developer guide

How the code is laid out, how to run the checks, and how changes reach a release. For using AutoReiv, see the [User guide](user-guide.md).

The working rules for changes (cards, checks, merging) are in [AGENTS.md](../AGENTS.md), with the always-on rules in [`.agents/rules/`](../.agents/rules/) and step-by-step skills in [`.agents/skills/`](../.agents/skills/).

## Set up a development copy

```bash
git clone https://github.com/jacobbweber/AutoReiv.git
cd AutoReiv
python -m venv .venv
# activate it (see the install guide), then:
pip install -e ".[dev]"
npm install                      # ESLint, Vitest and Playwright for the web front end
autoreiv serve --reload --port 8000
```

Use your own data folder for development (`AUTOREIV_DATA_DIR`) so tests and experiments never touch your everyday data. A second clone can run on another port next to your everyday copy.

On Windows, `scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000` restarts a development serve cleanly. It ignores any `AUTOREIV_*` variables in your shell, uses the configured or default data folder unless you pass `-DataDir`, `-WikiPath` or `-DbPath`, and prints the data folder it used.

## Code layout

```
src/web/               FastAPI app, routers, the HTML page and the browser code (static/modules)
src/application/       the agent kernel, model gateway, jobs, routines, skills and tools, settings, updates
src/domain/            models and rules: agents, memory, wiki, routines, safety
src/infrastructure/    SQLite storage, model provider adapters, the data folder resolver, backups
src/cli/               the `autoreiv` command
platform/              shipped agents (agents/<id>.md) and skills (skills/<id>/SKILL.md), read in place
deploy/                Windows service and Linux systemd scripts
scripts/               development helpers (restart_serve, live_qa, smoke_server)
templates/             the starter files Projects uses for a new code project
tests/                 pytest (unit, integration), Vitest (tests/unit/frontend), Playwright (tests/e2e)
```

Shipped agents and skills are read in place from `platform/`. Editing one in the app saves a copy in the data folder (`agents/<id>.md`, `skills/<id>/SKILL.md`) that wins over the shipped one.

## Checks

| What | Command |
|---|---|
| Python tests | `python -m pytest -q -n auto` |
| Python lint | `ruff check src tests` |
| Front-end lint | `npx eslint src/web/static tests/unit/frontend tests/e2e` |
| Front-end unit tests | `npx vitest run` |
| Browser smoke test | `npx playwright test tests/e2e/smoke.spec.js` |
| Fast preflight (about a minute) | `python .agents/skills/preflight/scripts/preflight.py --fast --base qa` |
| Release preflight (about 7 minutes) | `python .agents/skills/preflight/scripts/preflight.py --release` |

Tests never call a real model.

## Branches and releases

- Work happens on a short-lived branch off `qa` (for example `fix/card-NNN-short-name`) and is merged into `qa` with `--no-ff` after the checks pass.
- A release bumps the version on `qa` (`pyproject.toml`, `package.json`, `uv.lock`, the fallback in `src/application/system/update_service.py`), moves the changelog's Unreleased section under the new version, and passes the release preflight. Then `qa` is merged into `main` with `--no-ff`, the merge is tagged (`vX.Y.Z`, annotated), and `main` is merged back into `qa`.
- `main` only changes at a release.

## Project records

- Cards (one per change, with its status): [`.agents/cards/`](../.agents/cards/)
- Architecture decisions: [`docs/adr/`](adr/)
- Findings waiting for triage: [`docs/findings.md`](findings.md)
- Product, technology and structure notes, and the roadmap: [`steering/`](../steering/)
- Older design notes and specs, kept for history: [`docs/design/`](design/), [`docs/education/`](education/) and [`docs/archive_artifacts/`](archive_artifacts/)
- The 1.0 acceptance checklist: [`docs/acceptance-checklist-1.0.md`](acceptance-checklist-1.0.md)
