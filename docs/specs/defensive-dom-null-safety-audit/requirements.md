# Requirements Specification: Defensive DOM Query & Null-Safety Audit Across All Studio Interfaces

> **Spec Status**: Approved  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Card Reference**: [CARD-033](file:///.github/cards/CARD-033-defensive-dom-query-and-null-safety-audit-across-all-studio-interfaces.md)  

> **Primary Component**: AutoReiv Web Client Modules (`src/web/static/modules/`)

---

## 1. Executive Summary & Intent

Following the initial modularization of `app.js` in CARD-031 and CI test gates in CARD-032, **CARD-033** conducts an exhaustive defensive DOM audit across all 7 studio modules (`chat.js`, `routines.js`, `observability.js`, `forge.js`, `settings.js`, `docs.js`, `wiki.js`) and orchestrator (`app.js`). It replaces all remaining raw DOM queries with defensive helpers, guarantees 100% null-guarded event listeners via safe binding helpers, sanitizes all dynamic HTML interpolations, and introduces an automated static audit test in Vitest.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-DOM-001] Complete Helper Migration for All Studio Modules
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** perform all element selections in `src/web/static/modules/` through defensive helpers (`$`, `$query`, `$queryAll` from `dom.js`) rather than direct un-scoped `document.getElementById` or `document.querySelector` calls.

### [REQ-DOM-002] Defensive Event Binding Helper (`$on`)
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide and utilize a defensive event binding utility `$on(targetOrId, event, handler, options)` in `dom.js` that automatically guards against `null` or `undefined` elements without throwing runtime exceptions.

### [REQ-DOM-003] Strict XSS Sanitization for Dynamic HTML Content
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** sanitize all user-generated, agent-generated, and metadata strings interpolated into `innerHTML` via `escapeHtml()` across all studio modules.

### [REQ-DOM-004] Automated DOM Architecture Static Lint Rule
- **EARS Pattern**: State-Driven
- **Requirement**: The system **shall** provide an automated Vitest test (`tests/unit/frontend/dom_audit.test.js`) that parses all JavaScript modules under `src/web/static/modules/` and asserts zero direct `document.getElementById` or raw `document.querySelector` usage outside of `dom.js`.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: Zero direct `document.getElementById` or `document.querySelector` in any studio file outside `dom.js`.
- [ ] `AC-2`: All event listeners use `$on` or explicit null-guards (`if (el) el.addEventListener(...)` / `el?.addEventListener(...)`).
- [ ] `AC-3`: Vitest test `dom_audit.test.js` passes and prevents future architectural regressions.
- [ ] `AC-4`: `npm run preflight` passes 100% with all 5 gates green.
