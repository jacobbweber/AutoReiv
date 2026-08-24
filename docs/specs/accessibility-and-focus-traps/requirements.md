# Requirements Specification: Mobile & Keyboard Accessibility

> **Spec Status**: Approved  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Card Reference**: [CARD-038](file:///.github/cards/CARD-038-mobile-and-keyboard-accessibility.md)  

> **Primary Component**: AutoReiv Web SPA & Frontend Module Layer (`src/web/templates/index.html`, `src/web/static/modules/utils/accessibility.js`, `src/web/static/app.js`)

---

## 1. Executive Summary & Intent

**CARD-038** implements comprehensive keyboard accessibility, semantic ARIA landmarks, modal focus trapping, and screen-reader live regions across the AutoReiv Web SPA. It ensures compliance with standard accessibility practices, providing intuitive non-mouse keyboard navigation and mobile touch accessibility.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-A11Y-001] Semantic ARIA Roles & Screen Reader Landmarks
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** structure the UI with standard ARIA attributes: `role="tablist"` and `role="tab"` with dynamic `aria-selected="true|false"` on studio navigation buttons, `role="tabpanel"` on studio container views, `role="dialog"` with `aria-modal="true"` on modal overlays, and `aria-live="polite"` on dynamic chat streaming regions.

### [REQ-A11Y-002] Modal Focus Trapping & Escape Key Dismissal
- **EARS Pattern**: Event-Driven
- **Requirement**: When any modal or drawer is opened, the system **shall** trap keyboard focus within the modal's focusable elements (wrapping `Tab` and `Shift+Tab`), dismiss the modal on `Escape` keypress, and restore focus to the trigger element upon closure.

### [REQ-A11Y-003] Studio Navigation Arrow-Key Keyboard Controls
- **EARS Pattern**: Event-Driven
- **Requirement**: When focus resides within the studio tab list, the system **shall** cycle through studio tabs upon pressing `ArrowDown`/`ArrowRight` (forward) or `ArrowUp`/`ArrowLeft` (backward), automatically updating the active view and ARIA attributes.

### [REQ-A11Y-004] Accessibility Utilities & Automated Test Verification
- **EARS Pattern**: State-Driven
- **Requirement**: When executing `npm run test:unit:frontend` or `npm run preflight`, the system **shall** execute automated tests in `tests/unit/frontend/accessibility.test.js` validating focus trap wrapping, escape handling, and ARIA state transitions with 100% green status.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: All studio tabs have `role="tab"` and toggle `aria-selected` dynamically when activated.
- [ ] `AC-2`: All modals (`routineModal`, `wikiNewNoteModal`, `wikiMindMapModal`, `mermaidZoomModal`, `wikiGraphModal`) declare `role="dialog"`, `aria-modal="true"`, trap `Tab` navigation, and dismiss on `Escape`.
- [ ] `AC-3`: Arrow keys (`ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`) navigate studio tabs smoothly.
- [ ] `AC-4`: `npm run preflight` passes all 6 gates 100% cleanly.
