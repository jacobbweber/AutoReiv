# [CARD-369] Audit and Prune Dead UI Controls and Vestiges Across Studios

> **Status**: Ready  
> **Created**: 2026-09-19  
> **Spec Reference**: [docs/specs/audit-dead-ui/](file:///d:/Projects/Active/AutoReiv/docs/specs/audit-dead-ui/)  
> **Labels**: `type:chore`, `frontend`, `ui-ux`

---

## 1. Why / Intent
Systematically audit all studios and the application shell for dead UI elements, orphaned buttons, disconnected checkboxes, and obsolete navigation rails left behind after architectural evolutions, pruning them for an honest, maintainable interface.

---

## 2. Three Beats

### Beat 1: What Jacob Means
A thorough audit across all 11 studios to locate and eliminate dead DOM levers, non-functional modals, and orphaned navigation bars that do nothing or are suppressed by CSS, while ensuring all active form submit triggers and functional buttons are preserved.

### Beat 2: What AutoReiv Does Now
- An unhooked 65-line Mermaid Pan-Zoom Inspector modal (`#mermaidZoomModal`) exists in `index.html`. In Chat Studio, rendered Mermaid diagrams show an "Inspect & Zoom" button that does nothing because `callbacks.openMermaidInspector` was never implemented.
- The 52px left icon rail (`<nav id="appRail">`) from early CARD-138 sits suppressed in `index.html` via `display: none !important;` because Agent Desktop replaced it with the bottom dock (`#dockBar`, CARD-305). `app.js` still registers listeners on `railBtns`.
- `agent-desktop.js` retains dead positioning code calculating coordinates for an obsolete `#sidebar` from a nonexistent `sessions` window.
- All 167 input/select/textarea controls and submit buttons (`#promptsEditorSaveBtn`, `#saveToneBtn`) are confirmed functional.

### Beat 3: What Will Change
- Prune `#mermaidZoomModal` and its child buttons from `index.html`, `app.js`, and `modal.js`. Remove the non-functional "Inspect & Zoom" overlay button in `chat.js`.
- Prune `<nav id="appRail">` and its child buttons from `index.html`, and clean up `railBtns` in `app.js`.
- Prune dead `sessionsWin` / `#sidebar` positioning code from `agent-desktop.js`.
- Update legacy test assertions in `workbench_shell.test.js` and `factory_studio.test.js` to assert on modern dock navigation instead of obsolete pre-desktop rails.
- Add `tests/unit/frontend/dom_audit.test.js` to prevent regressions.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `#mermaidZoomModal` and its children are pruned from `index.html` and `app.js`.
- [ ] Rendered Mermaid diagrams in Chat Studio render cleanly without dead inspect buttons.
- [ ] `<nav id="appRail">` and `railBtns` are pruned from `index.html` and `app.js`.
- [ ] Dead `#sidebar` positioning in `agent-desktop.js` is pruned.
- [ ] All 11 studios continue to open, render, and function properly.
- [ ] All 7 preflight gates pass cleanly (Vitest, pytest, ruff, eslint, rtm-sync).

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to active studio functionality.
- Single isolated `feat/card-369-prune-dead-ui` branch cut from `qa` upon Jacob's `build` approval.
