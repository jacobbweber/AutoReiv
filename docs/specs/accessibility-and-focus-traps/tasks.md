# Task Breakdown: Mobile & Keyboard Accessibility

> **Spec Status**: Implemented  
> **Target Release**: Milestone 11 (v0.11.0)  
> **Card Reference**: [CARD-038](file:///.github/cards/CARD-038-mobile-and-keyboard-accessibility.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/accessibility-and-focus-traps/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/accessibility-and-focus-traps/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Pure Accessibility Utility Module & Unit Testing
- [x] **Task 1.1**: Author `src/web/static/modules/utils/accessibility.js` with focus trap, tab navigation, and ARIA syncing helper functions (`[REQ-A11Y-001]`, `[REQ-A11Y-002]`, `[REQ-A11Y-003]`).
- [x] **Task 1.2**: Author unit test suite `tests/unit/frontend/accessibility.test.js` verifying focus trapping, wrap-around logic, arrow key navigation, and ARIA attributes (`[REQ-A11Y-004]`).

### Slice 2: HTML Template ARIA Enhancements & Studio Integration
- [x] **Task 2.1**: Update `src/web/templates/index.html` with semantic ARIA roles (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `role="dialog"`, `aria-modal="true"`, `aria-live="polite"`) (`[REQ-A11Y-001]`).
- [x] **Task 2.2**: Integrate `accessibility.js` into `src/web/static/app.js` and studio modules to manage modal open/close focus trapping and studio tab keyboard navigation (`[REQ-A11Y-002]`, `[REQ-A11Y-003]`).

### Slice 3: Verification, Pre-Flight & Gate Closure
- [x] **Task 3.1**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-A11Y-004]`).
- [x] **Task 3.2**: Author ADR-0038 and sync `docs/rtm.json` with `[REQ-A11Y-001]` through `[REQ-A11Y-004]`.
- [x] **Task 3.3**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

