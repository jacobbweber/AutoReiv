# Requirements Specification: Audit and Prune Dead UI Controls

> **Spec Status**: In Review  
> **Target Release**: Sprint 2026-Q3  
> **Primary Component**: Web Frontend / Studio Navigation & Modals  
> **Linked Card**: [CARD-369](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-369-audit-and-prune-dead-ui-controls-and-vestiges-across-studios.md)

---

## 1. Executive Summary & Intent
Over multiple architectural iterations (CARD-138 slim icon rail, CARD-139 3-surface mobile header, CARD-296 in-studio Chat sessions drawer, CARD-305 Agent Desktop dock), several navigation rails, sidebars, and experimental modal dialogs were superseded and suppressed with `display: none !important;`. Furthermore, an experimental Mermaid pan-zoom inspector modal was scaffolded but never implemented, leaving misleading "Inspect & Zoom" buttons on rendered diagrams that do nothing when clicked.

This specification defines the requirements for systematically auditing, pruning, and retiring these dead DOM elements and unhooked listeners across `src/web/templates/index.html` and static JS modules, ensuring every visible control in AutoReiv is honest, functional, and purposeful.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-PRUNE-001]: Elimination of Unimplemented Mermaid Zoom Inspector
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL NOT render or expose unimplemented Mermaid pan-zoom inspector modal DOM or misleading inspector action buttons.`
- **Acceptance Criteria**:
  - [ ] `#mermaidZoomModal` and its child elements (`#mermaidZoomOutBtn`, `#mermaidZoomLevel`, `#mermaidZoomInBtn`, `#mermaidZoomResetBtn`, `#mermaidFullscreenBtn`, `#mermaidCloseModalBtn`, `#mermaidViewport`, `#mermaidCanvas`) are removed from `index.html`.
  - [ ] `src/web/static/app.js` does not reference `'mermaidZoomModal'` in `allModals`.
  - [ ] `src/web/static/modules/ui/modal.js` does not query `#mermaidCloseModalBtn`.
  - [ ] Rendered Mermaid diagrams in Chat Studio do not show a non-functional "Inspect & Zoom" button overlay; diagrams render inline cleanly with responsive horizontal scroll.

### [REQ-PRUNE-002]: Retirement of Superseded Pre-Desktop Navigation Rail
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL NOT include vestigial pre-desktop icon rail DOM elements superseded by the Agent Desktop dock.`
- **Acceptance Criteria**:
  - [ ] `<nav id="appRail">` (and its child surface triggers `#railBtnChat`, `#railBtnVault`, `#railBtnFleet`, `#railBtnFactory`, `#railBtnSettings`) is removed from `index.html`.
  - [ ] `src/web/static/app.js` does not maintain or listen to `railBtns`.
  - [ ] CSS rules suppressing `#appRail` under `body.radical-desktop-demo` are retired.

### [REQ-PRUNE-003]: Cleanup of Orphaned Desktop Sidebar Positioning Code
- **Type**: State-Driven
- **EARS Statement**: `WHILE running Agent Desktop, THE SYSTEM SHALL NOT attempt to calculate or apply window positioning coordinates to nonexistent sidebar elements.`
- **Acceptance Criteria**:
  - [ ] In `src/web/static/modules/ui/agent-desktop.js`, lines 594–616 referencing `windows.get('sessions')` and `$('sidebar')` are removed.
  - [ ] `toggleSidebarBtn` in `app.js` does not attempt to toggle classes on an obsolete sidebar; Chat sessions drawer toggle in `chat.js` and `agent-desktop.js` remains intact.

### [REQ-PRUNE-004]: Verification of Active Studio Controls
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL preserve all form submit triggers, cross-studio bridges, and mobile responsiveness drawers that are actively functional.`
- **Acceptance Criteria**:
  - [ ] `<button type="submit" id="promptsEditorSaveBtn">` is preserved.
  - [ ] `<button type="submit" id="saveToneBtn">` is preserved.
  - [ ] `<button id="educationAmpWatchLuminaBtn">` is preserved and functional.
  - [ ] `<button id="wikiMobileDrawerBtn">` and `#wikiDrawerCloseBtn` are preserved and functional.
  - [ ] All 167 active input, select, and textarea controls remain fully functional.

---

## 3. Non-Functional & Boundary Constraints
- **Zero Regressions**: No active studio features, dock launchers, or modal workflows shall be broken.
- **Test Integrity**: Legacy test files (`workbench_shell.test.js`, `surface_navigation.test.js`, `factory_studio.test.js`) are updated to reflect the modern dock navigation architecture.
- **Accessibility**: Modals remaining in the system maintain valid `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` attributes.

---

## 4. Out of Scope
- Redesigning the Agent Desktop dock or studio layouts (governed by `.agents/rules/ui-ux-design.md`).
- Adding new studio features or interactive help panels (parked under CARD-331).
