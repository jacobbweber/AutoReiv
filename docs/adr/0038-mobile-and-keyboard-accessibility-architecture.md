# ADR-0038: Mobile and Keyboard Accessibility Architecture

## Context and Problem Statement
Prior to this work, the AutoReiv Web SPA was primarily mouse- and touch-navigated without formal ARIA semantics (`role="tablist"`, `role="tab"`, `role="tabpanel"`, `role="dialog"`), modal focus trapping, or keyboard arrow navigation. Power users and screen reader assistive technologies lacked standard navigation primitives.

## Decision Drivers
- **WCAG / WAI-ARIA Standards**: Provide standard ARIA tablist patterns, dynamic `aria-selected`, and `aria-live` regions.
- **Focus Safety in Modals**: Prevent keyboard focus from leaking behind active modals (`Tab` / `Shift+Tab` wrapping, `Escape` key dismissal).
- **Zero-Dependency Lightweight Implementation**: Implement pure utility functions (`accessibility.js`) without heavy external UI dependencies.

## Considered Options
1. **Option 1**: Introduce heavy external headless UI libraries (e.g. Radix, HeadlessUI).
2. **Option 2 (Accepted)**: Author lightweight, pure vanilla JS accessibility utilities (`src/web/static/modules/utils/accessibility.js`) integrated into `app.js` and HTML templates.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Seamless keyboard navigation (`ArrowRight`/`ArrowDown`/`ArrowLeft`/`ArrowUp`/`Home`/`End`) across studio tabs.
- Hermetic modal focus trapping and universal `Escape` dismissal.
- Full screen reader compatibility with zero external bundle bloat.
- 10 new Vitest unit tests in `tests/unit/frontend/accessibility.test.js`.

### Negative Consequences / Trade-offs
- Manual maintenance of ARIA attributes when adding new modals or tab panels.
