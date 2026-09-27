---
trigger: glob
globs: 'src/web/**'
description: Frontend SPA invariants (native ES modules, no build step).
---
# Frontend

- Native ES modules, no build step. No framework or bundler without an ADR.
- Every interactive control has a stable `id` or `data-testid`.
- DOM access is null-safe: use the helpers in `src/web/static/modules/dom.js`; never assume an element exists.
- Each studio exports an `initXxx()` that `app.js` runs inside its own try/catch. One broken studio must not break page load.
- No inline `onclick="..."` in HTML strings; bind listeners in the module or use delegation.
- No silent `catch (e) {}`; log or show the error.
- API calls go through `src/web/static/modules/services/`; never duplicate fetch logic in a studio.
- Pure logic (formatters, reducers, parsers) lives in its own module with a Vitest test in `tests/unit/frontend/`.
- Tests on fixed registries (agents, studios, tabs) assert the exact set, never `length > 0`.
- When a built-in entity changes, update the first-paint markup in `src/web/templates/index.html` and its template test together.
- UI work: open skill `ui-review` before styling.
