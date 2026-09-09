# [CARD-205] Adopt Multi-Window Agent Desktop UI and Align Automated Verification

> **Status**: In Review
> **Created**: 2026-09-09
> **Spec Reference**: docs/demos/ui-radical-04-agent-desktop.md
> **Labels**: `type:ui`, `type:architecture`, `type:testing`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Adopt the Multi-Window Agent Desktop UI as Official**:
   - Formally adopt the OS-style multi-window desktop interface on the `qa` staging branch.
   - The user experience centers on a desktop stage (`#desktopStage`) with a bottom application dock (`#desktopDock`).
   - Clicking dock icons launches studios (Chat, Wiki, Projects, Agents/Forge, Factory, Routines, Observability, Settings, Prompts, Sessions) as draggable, resizable, stackable floating windows.
2. **Fix Factory Orchestrator Crash (11 Pytest Failures)**:
   - In `src/application/agent_training_factory/orchestrator.py`, assign `self.store = store` in `FactoryOrchestrator.__init__` so background phase advances and verification batteries never raise `AttributeError: 'FactoryOrchestrator' object has no attribute 'store'`.
3. **Fix DOM Safety Rule in Agent Desktop (1 Vitest Failure)**:
   - In `src/web/static/modules/ui/agent-desktop.js`, replace raw `document.getElementById` with the null-safe `$` helper from `dom.js` to satisfy `REQ-DOM-001`.
4. **Update Playwright Smoke Tests for Desktop Interaction**:
   - Modernize `tests/e2e/smoke.spec.js` to align with the Desktop OS paradigm:
     - TC-1: Verify `#desktopStage` and `#desktopDock` mount on first load, click `#dock-chat` to launch Chat window, and verify chat input, agent switcher, and message stream elements attach.
     - TC-2: Navigate studios by clicking dock launchers (`#dock-routines`, `#dock-observability`, `#dock-agents`, `#dock-settings`, `#dock-wiki`) and verify respective studio window containers open with their essential controls.
     - TC-3: Verify interactive modals (Wiki note, Mind Map, Routines) open and dismiss cleanly within the window environment.
     - TC-4: Verify agent switcher in the Chat window title bar synchronizes active agent state.

---

### Beat 2: What AutoReiv Does Now
1. **Desktop Code on `qa` without Card**:
   - The multi-window desktop was merged directly to `qa` across commits `55fb929`, `5a258f8`, and `fb64945`.
2. **Pytest Regressions in Agent Training Factory**:
   - 11 unit and integration tests fail with `AttributeError: 'FactoryOrchestrator' object has no attribute 'store'` because `self.store = store` was omitted during constructor refactoring.
3. **Vitest DOM Query Rule Violation**:
   - `tests/unit/frontend/dom_audit.test.js` fails because `agent-desktop.js:232` queries `document.getElementById('agentSelect')` directly.
4. **Playwright Smoke Test Suite Failing**:
   - All 4 smoke tests fail with timeouts because they expect the legacy single-column app shell where `#appRail` and `#view-chat` were immediately visible on page load. In the desktop paradigm, `#appRail` is hidden and windows must be launched via the dock.

---

### Beat 3: What Will Change
1. **Backend Bug Fix**:
   - In `src/application/agent_training_factory/orchestrator.py`, add `self.store = store` at line 53.
2. **Frontend DOM Guard**:
   - In `src/web/static/modules/ui/agent-desktop.js`, change `document.getElementById('agentSelect') || document.getElementById('chatTopBarAgentSelect')` to `$('agentSelect') || $('chatTopBarAgentSelect')`.
3. **Playwright Smoke Suite Modernization**:
   - In `tests/e2e/smoke.spec.js`:
     - Update tests to click `#dock-chat`, `#dock-routines`, `#dock-observability`, `#dock-agents`, `#dock-settings`, and `#dock-wiki`.
     - Assert that clicking a dock launcher brings up the corresponding studio window in `#desktopWindowLayer`.
4. **Changelog & Documentation**:
   - Update `CHANGELOG.md [Unreleased]` with CARD-205 details.
   - Validate full preflight (`ruff`, `pytest`, `eslint`, `vitest`, `playwright`, and `verify_rtm.py`).

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1 (Backend Factory Orchestrator Restored)**: `self.store` is properly assigned in `FactoryOrchestrator.__init__`. All 11 failing Agent Training Factory tests pass cleanly via `pytest`.
- [x] **AC-2 (Frontend Defensive DOM Compliance)**: `agent-desktop.js` uses null-safe `$` helpers from `dom.js`. `npm run test:unit:frontend` passes 100% (including `dom_audit.test.js`).
- [x] **AC-3 (Playwright Smoke Suite Adapted to Desktop)**: `npm run test:smoke` passes 100% against the desktop dock launcher and floating window architecture.
- [x] **AC-4 (Full Preflight Verification)**: `python .agents/skills/rtm-sync/scripts/preflight.py` passes all 6 gates with zero errors.
- [x] **AC-5 (Changelog Recorded)**: `CHANGELOG.md` under `[Unreleased]` captures CARD-205.

---

## 3. Constraints & Invariants
- Follows "How we walk cards with Jacob" in `AGENTS.md`.
- No code written until Jacob approves this card with "build".
- Local `qa` branch workflow. Zero push, tag, or merge to `main`.
