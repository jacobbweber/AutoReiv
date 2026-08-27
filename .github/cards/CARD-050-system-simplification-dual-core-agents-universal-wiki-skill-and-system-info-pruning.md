# [CARD-050] System Simplification: Dual Core Agents, Universal Wiki Skill & System Info Pruning

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/system-simplification/
> **Labels**: `type:refactor`, `quality-gate`

---

## 1. Why / Intent
Consolidate built-in baseline agents down to two clearly defined identities (`assistant` and `autoreiv`), elevate the Wiki capability into a universal `WikiSkill` accessible to all agents, and prune the System Info / Docs Studio and associated services from the application surface to reduce cognitive load and documentation drift.

---

## 2. What to Build
1. **Core Built-in Baseline Agents (`src/domain/agents/profiles.py`)**:
   - `assistant`: General-purpose daily workflow assistant and task coordinator with `task_tracker_*`, `wiki_*`, and `delegate_task` tools.
   - `autoreiv`: Platform SRE and self-introspecting diagnostic agent with `inspect_health`, `get_system_logs`, `get_recent_errors`, `test_connectivity`, `system_info`, `cli_exec`, `wiki_*`, and `delegate_task` tools.
   - Backward-compatibility aliases in `SupervisorOrchestrator` (`general-assistant` -> `assistant`, `system-agent` / `sysadmin` / `librarian` -> `autoreiv` or `assistant`).
2. **Universal Wiki Skill (`src/application/skills/wiki_skill.py`)**:
   - Refactor `LibrarianSkill` -> `WikiSkill` (exposing `wiki_note_*`, `wiki_overview`, `wiki_graph`).
   - Register `WikiSkill` tools across built-in and custom agents.
3. **UI & Service Pruning**:
   - Remove Docs / System Info tab and drawer from `src/web/templates/index.html` and `src/web/static/app.js`.
   - Remove `src/web/static/modules/studios/docs.js`.
   - Remove `SystemInfoService` and `SystemDocumentationService` from `src/application/web/`.
   - Clean up `src/web/routers/system.py` to retain `/health`, `/api/health`, and `/api/memory/facts`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-SIMP-001]: Exactly 2 core built-in profiles (`assistant`, `autoreiv`) active in `BUILTIN_PROFILES`.
- [x] [REQ-SIMP-002]: `WikiSkill` exported and attached as a universal skill for both core agents and custom agents.
- [x] [REQ-SIMP-003]: Docs / System Info studio removed from frontend navigation and backend services.
- [x] All unit and integration tests pass cleanly via `pytest`.
- [x] All frontend unit tests pass cleanly via `npm run test:unit:frontend`.
- [x] Playwright smoke suite passes cleanly via `npm run test:smoke`.
- [x] Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to core chat streaming, wiki vault, settings, routines, or observability.
- Single isolated `feat/*` branch cut from `qa`.

