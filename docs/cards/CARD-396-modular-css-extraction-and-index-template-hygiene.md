---
id: CARD-396
title: "Modular CSS Extraction and Index Template Hygiene"
status: In Review
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:frontend
  - domain:ui
---

# [CARD-396] Modular CSS Extraction and Index Template Hygiene

> **Status**: In Review  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:frontend`, `domain:ui`  

---

## 1. Why / Intent (Beat 1)

`src/web/templates/index.html` has swollen to **5,998 lines**, making it the largest file in the codebase.
Crucially, **1,325 lines of that file** (lines 71–1,396) are raw CSS crammed directly into a monolithic `<style>` tag in the HTML head.
No `src/web/static/css/` directory exists.
Inlining all CSS inside `index.html`:
1. Prevents browser HTTP caching of stylesheets across page reloads.
2. Clutters template context for LLMs and developers.
3. Violates separation of concerns between presentation styles and HTML document structure.

---

## 2. What AutoReiv Does Now (Beat 2)

- All CSS rules (theme variables, mobile inset locks, radical desktop window styling, studio layouts, scrollbar tweaks, animation keyframes) reside in a single `<style>` block in `index.html`.
- `index.html` is served on every root request with the inline CSS payload repeated every time.
- No standalone `.css` files exist under `src/web/static/`.

---

## 3. What Will Change (Beat 3)

- Create `src/web/static/css/` directory with structured modular stylesheets:
  - `src/web/static/css/base.css`: CSS custom properties, base reset, mobile inset lock, and overscroll prevention.
  - `src/web/static/css/desktop.css`: Radical agent desktop windowing rules, docking styles, and window header controls.
  - `src/web/static/css/studios.css`: Studio-specific layout rules (Education panels, Factory columns, Forge workshops, Wiki tree).
  - `src/web/static/css/components.css`: Custom scrollbars, badges, drawers, toasts, and animations.
- Replace the 1,325-line `<style>` tag in `src/web/templates/index.html` with clean `<link rel="stylesheet">` tags.
- Update `package.json` formatting / linting targets if needed to ensure CSS formatting is verified.
- Add Vitest test to assert that `index.html` contains no monolithic inline `<style>` block exceeding 50 lines.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Deleted Inline Styles**:
  - The entire 1,325-line `<style>...</style>` block in `src/web/templates/index.html` (lines 71–1,396).
- **Redundant Style Overrides**:
  - Any duplicate or conflicting CSS rules discovered during decomposition.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL serve frontend stylesheet assets as external static files from `src/web/static/css/`.
- **Ubiquitous**: THE SYSTEM SHALL keep `src/web/templates/index.html` under 4,800 lines with zero monolithic `<style>` blocks.
- **State-Driven**: WHILE loading the web interface, THE BROWSER SHALL correctly apply all desktop windowing, theme engine variables, and studio layouts identically to the pre-refactor state.
- **Negative Assertion**: Automated tests shall assert that `src/web/templates/index.html` does not contain inline `<style>` blocks with more than 50 lines of CSS.
- **Negative Assertion**: Automated tests shall verify that all referenced `.css` files exist on disk and return HTTP 200 via the static file handler.

---

## 6. Constraints & Verification Plan

- Standard honor constraints apply.
- Zero visual or functional regressions in existing desktop windowing, chat interface, or studio layouts.
- Feature branch cut from `qa`: `feat/card-396-modular-css-extraction`.
- Verification via `npm run test:unit:frontend`, `npx playwright test tests/e2e/smoke.spec.js`, and `npm run lint:frontend`.
