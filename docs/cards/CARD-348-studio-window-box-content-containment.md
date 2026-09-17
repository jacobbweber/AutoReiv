# [CARD-348] Studio Window Box Content Containment

> **Status**: Done
> **Created**: 2026-09-17
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:frontend`, `domain:ui-ux`, `subsystem:agent-desktop`

---

## 1. Why / Intent

When opening certain studios on the radical agent desktop (notably Factory and Lumina), the studio content view spills outside the bottom border of the desktop window box instead of remaining enclosed within the window chrome and scrolling internally.

This happens because CSS rules for Factory (`#view-factory.desktop-view-hosted`) and Lumina (`#view-lumina.desktop-view-hosted`) applied `height: 100% !important` to the hosted view root. Because hosted studio views use `position: fixed !important`, setting `height: 100%` makes them take 100% of the entire browser viewport height rather than the window body height (`var(--dw-h)`). Since the window top is offset below the desktop titlebar, this extra height pushes the studio content and its inner scrollable elements hundreds of pixels below the bottom edge of the window frame.

---

## 2. The Three Beats

1. **What Jacob means**:
   - When a studio window (like Factory Studio or Lumina Cinema) is opened or resized, all of its inner controls, textareas, cards, and scrollable panels must stay completely captured inside the window frame.
   - The content must never spill past the bottom border of the window box or overlap the desktop wallpaper and dock below.
   - The content inside the window should scroll within the window frame.

2. **What AutoReiv does now**:
   - In `src/web/templates/index.html` lines 1023–1029 and 1036–1042, `#view-factory.desktop-view-hosted` and `#view-lumina.desktop-view-hosted` share a CSS rule with their inner studio containers (`#factoryStudio` and `#luminaStudio`) that sets `height: 100% !important; max-height: 100% !important;`.
   - Because `.tab-view.desktop-view-hosted` uses `position: fixed !important`, `height: 100%` resolves against the browser viewport (100vh) rather than `var(--dw-h)` (the measured pixel height of the window body).
   - This overrides the standard hosted height (`height: var(--dw-h, 30rem) !important`), making the studio container 100% of the viewport height and pushing the bottom of the studio out of the window frame.
   - Additionally, on screen widths <= 1023px, line 320 sets `#view-education { height: 100% !important; }` which would cause a similar spillover if Education is hosted in desktop mode.

3. **What will change**:
   - `body.radical-desktop-demo #view-factory.desktop-view-hosted` is removed from the `height: 100% !important` rule so that `#view-factory` adheres strictly to `height: var(--dw-h, 30rem) !important` set by `.tab-view.desktop-view-hosted`.
   - The inner container `body.radical-desktop-demo #view-factory.desktop-view-hosted #factoryStudio` retains `height: 100% !important; min-height: 0 !important; overflow: hidden !important;`, filling 100% of the window body height while letting `#factoryPipelineView` scroll internally.
   - `body.radical-desktop-demo #view-lumina.desktop-view-hosted` is similarly decoupled so `#view-lumina` uses `var(--dw-h)` and only `#luminaStudio` has `height: 100% !important`.
   - `#view-education` under `@media (max-width: 1023px)` is scoped to `:not(.desktop-view-hosted)` so hosted windows preserve their window-bounded height.
   - Vitest automated tests verify that all hosted studio views stay bounded to `var(--dw-h)` and do not leak `height: 100%` onto fixed-position view containers.

---

## 3. What to Build

- **`src/web/templates/index.html`**:
  - Update `#view-factory` desktop rules (lines 1023–1029) to apply `height: 100% !important` strictly to `#factoryStudio`, keeping `#view-factory.desktop-view-hosted` sized to `var(--dw-h)`.
  - Update `#view-lumina` desktop rules (lines 1036–1042) to apply `height: 100% !important` strictly to `#luminaStudio`, keeping `#view-lumina.desktop-view-hosted` sized to `var(--dw-h)`.
  - Scope `#view-education` mobile media query rule (line 317) to `#view-education:not(.desktop-view-hosted)`.
- **`tests/unit/frontend/studio_window_containment_348.test.js`**:
  - Add unit tests verifying CSS selectors for Factory, Lumina, and Education in `index.html` do not impose `height: 100% !important` on `.desktop-view-hosted` view roots.
- **`src/web/static/app.js`**:
  - Bump cache-buster query version if referenced.

---

## 4. Acceptance Criteria (Definition of Done)

- [x] `#view-factory.desktop-view-hosted` does not have `height: 100% !important;` and inherits `height: var(--dw-h, 30rem) !important;` from `.tab-view.desktop-view-hosted`.
- [x] `#factoryStudio` inside `#view-factory.desktop-view-hosted` retains `height: 100% !important; min-height: 0 !important; overflow: hidden !important;`.
- [x] `#view-lumina.desktop-view-hosted` does not have `height: 100% !important;` and inherits `height: var(--dw-h, 30rem) !important;` from `.tab-view.desktop-view-hosted`.
- [x] `#luminaStudio` inside `#view-lumina.desktop-view-hosted` retains `height: 100% !important; min-height: 0 !important; overflow: hidden !important;`.
- [x] `#view-education` mobile breakpoint does not apply `height: 100% !important;` to `.desktop-view-hosted`.
- [x] Factory prompt rubric, context variables, and textarea stay fully captured inside the window body and scroll smoothly with `#factoryPipelineView`.
- [x] Window resizing via chrome resize handles updates Factory and Lumina view dimensions in lockstep without spilling out.
- [x] All 517+ frontend unit tests in `tests/unit/frontend/` pass with zero regressions (now 522 tests passing).
- [x] New unit test suite `tests/unit/frontend/studio_window_containment_348.test.js` passes.

---

## 5. Constraints & Honor Flags

- Preserves factory deep-link scoping from CARD-314.
- Preserves Lumina compose and stage view switching from CARD-328.
- Zero changes to DOM structure or IDs.
- Single isolated `feat/studio-window-containment-348` branch cut from `qa`.

