# Task Breakdown: Defensive DOM Query & Null-Safety Audit Across All Studio Interfaces

> **Spec Status**: Implemented  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Card Reference**: [CARD-033](file:///.github/cards/CARD-033-defensive-dom-query-and-null-safety-audit-across-all-studio-interfaces.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/defensive-dom-null-safety-audit/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/defensive-dom-null-safety-audit/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Defensive DOM & Event Helper Infrastructure
- [x] **Task 1.1**: Enhance `src/web/static/modules/dom.js` with `$on()`, robust root scoping in `$query()` / `$queryAll()`, and safe return values (`[REQ-DOM-002]`).
- [x] **Task 1.2**: Write initial failing Red Vitest test (`tests/unit/frontend/dom_audit.test.js`) asserting zero raw DOM queries across `src/web/static/modules/` (`[REQ-DOM-004]`).

### Slice 2: Full Studio DOM Refactoring & Null-Guarding
- [x] **Task 2.1**: Audit and refactor `docs.js`, `settings.js`, and `observability.js` to use `$`, `$query`, `$queryAll`, and `$on` (`[REQ-DOM-001]`).
- [x] **Task 2.2**: Audit and refactor `forge.js`, `routines.js`, `chat.js`, and `wiki.js` to use `$`, `$query`, `$queryAll`, and `$on` (`[REQ-DOM-001]`).
- [x] **Task 2.3**: Verify all dynamic HTML interpolations pass through `escapeHtml()` across all studios (`[REQ-DOM-003]`).

### Slice 3: Verification & Pre-Flight Gate Closure
- [x] **Task 3.1**: Run `npm run test:unit:frontend` and verify `dom_audit.test.js` passes cleanly.
- [x] **Task 3.2**: Run `npm run preflight` to verify all 5 pre-flight gates pass 100%.
- [x] **Task 3.3**: Create ADR-0033 and sync `docs/rtm.json` with `[REQ-DOM-001]` through `[REQ-DOM-004]`.
- [x] **Task 3.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

