# Implementation Tasks: Audit and Prune Dead UI Controls

> **Spec Status**: In Review  
> **Linked Card**: [CARD-369](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-369-audit-and-prune-dead-ui-controls-and-vestiges-across-studios.md)  
> **Requirements**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/audit-dead-ui/requirements.md)  
> **Design**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/audit-dead-ui/design.md)

---

## Task List

- [ ] **Task 1: [RED] Add DOM Audit Test Suite**
  - Create `tests/unit/frontend/dom_audit.test.js`.
  - Assert that `#mermaidZoomModal` and `#appRail` are NOT present in `index.html`.
  - Assert that all 11 studio views and active form triggers (`#promptsEditorSaveBtn`, `#saveToneBtn`, `#educationAmpWatchLuminaBtn`, `#wikiMobileDrawerBtn`) ARE present.
  - Run test to observe expected failure (RED).

- [ ] **Task 2: [GREEN] Prune Dead Mermaid Modal & Clean Up JS**
  - In `src/web/templates/index.html`, remove `#mermaidZoomModal` and its children (lines 5281–5345).
  - In `src/web/static/app.js`, remove `'mermaidZoomModal'` from `allModals`.
  - In `src/web/static/modules/ui/modal.js`, remove `#mermaidCloseModalBtn` from close button query selectors.
  - In `src/web/static/modules/studios/chat.js`, remove `.mermaid-actions` inspect button and `callbacks.openMermaidInspector`.

- [ ] **Task 3: [GREEN] Prune Vestigial #appRail & Orphaned Sidebar Positioning**
  - In `src/web/templates/index.html`, remove `<nav id="appRail">` (lines 1379–1422) and update CSS suppression rule.
  - In `src/web/static/app.js`, remove `railBtns` object and its listeners.
  - In `src/web/static/modules/ui/agent-desktop.js`, remove dead `sessionsWin` / `sidebar` positioning code (lines 594–616).

- [ ] **Task 4: [REFACTOR & ALIGN] Update Legacy Tests**
  - Update `tests/unit/frontend/workbench_shell.test.js` to assert on modern workbench canvas and active tabs without obsolete `#appRail`.
  - Update `tests/unit/frontend/factory_studio.test.js` to assert on Factory Studio dock launcher without obsolete `#railBtnFactory`.

- [ ] **Task 5: Verification & Preflight Gates**
  - Run `npm run test:unit:frontend`.
  - Run `npm run lint:frontend`.
  - Run `uv run ruff check .`.
  - Run `uv run pytest tests/unit/kernel/`.
  - Run `uv run python .agents/skills/rtm-sync/scripts/preflight.py`.
