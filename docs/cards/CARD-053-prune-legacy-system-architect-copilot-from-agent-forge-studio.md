# [CARD-053] Prune Legacy System Architect CoPilot from Agent Forge Studio

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/prune-agent-forge-copilot/
> **Labels**: `type:refactor`, `milestone:17`

---

## 1. Why / Intent
Clean up the obsolete legacy "System Architect Co-Pilot" chat sidebar from Agent Forge Studio. AutoReiv will manage agent creation tools via first-class skill packs in the future, and removing this embedded chat interface eliminates dead code, declutters the mobile/desktop layout, and lets the RPG Character Sheet cards expand cleanly to full width.

---

## 2. What to Build
1. **HTML Template Cleanup (`src/web/templates/index.html`)**:
   - Remove the right column `<div class="lg:col-span-5 xl:col-span-4 flex flex-col ...">` containing Co-Pilot header, message stream, starter chips, and prompt input form.
   - Update the Character Sheet container from a constrained 7-8 column layout to a spacious, responsive workspace.
2. **JavaScript Module Cleanup (`src/web/static/modules/studios/forge.js`)**:
   - Remove Co-Pilot DOM element queries (`copilotForm`, `copilotInput`, `copilotMessages`, `applyBlueprintBtn`, `copilotChips`).
   - Remove `appendCopilotMessage`, `extractAndOfferBlueprint`, `checkForBlueprint`, and chat streaming event listeners.
3. **Automated Test Updates**:
   - Verify Vitest frontend tests and Playwright smoke tests pass cleanly.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-PRUNE-001]`: Remove Co-Pilot DOM markup and prompt input from `view-agents` in `src/web/templates/index.html`.
- [x] `[REQ-PRUNE-002]`: Agent Forge Character Sheet cards expand cleanly across full workspace width on desktop and mobile.
- [x] `[REQ-PRUNE-003]`: Remove legacy Co-Pilot JS functions and event listeners from `src/web/static/modules/studios/forge.js`.
- [x] `[REQ-PRUNE-004]`: All automated test suites (Pytest, Vitest, Playwright smoke, ESLint, Ruff) pass with 100% green status.

---

## 4. Constraints & Honor Flags
- Strict isolated `feat/prune-agent-forge-copilot` branch cut from `qa`.
- Zero breaking changes to existing passing tests or agent profile saving functionality.

