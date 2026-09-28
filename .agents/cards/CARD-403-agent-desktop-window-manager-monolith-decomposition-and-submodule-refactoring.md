---
id: CARD-403
title: "Agent Desktop Window Manager Monolith Decomposition and Submodule Refactoring"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:frontend
  - domain:desktop
---

# [CARD-403] Agent Desktop Window Manager Monolith Decomposition and Submodule Refactoring

> **Status**: Done
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:frontend`, `domain:desktop`  

---

## 1. Why / Intent (Beat 1)

In accordance with `.agents/rules/code-hygiene-and-pruning.md` (Monolith Decomposition Guidelines), files exceeding 800 lines cause context blindness and hinder maintainability.

`src/web/static/modules/ui/agent-desktop.js` has grown into a 1,894-line monolith combining dock launchers, desktop DOM chrome, geometry calculations, grid snapping, layout math, desktop preferences/localStorage persistence, window shell creation, pointer drag & resize event handling, z-stack ordering, window state lifecycle (minimize, close, maximize, mobile layout), organize menu, layout presets, and HITL dialog host enhancements.

We must decompose this monolith into cohesive submodules under `src/web/static/modules/ui/agent_desktop/`, keeping all submodules strictly under 800 lines, keeping the root coordinator `agent-desktop.js` strictly under 1,000 lines, and guaranteeing 100% backward compatibility for all exported functions and constants.

---

## 2. What AutoReiv Does Now (Beat 2)

1. A single 1,894-line file `src/web/static/modules/ui/agent-desktop.js` handles:
   - Dock launcher manifests (`DOCK_LAUNCHERS`).
   - Desktop DOM chrome initialization (`ensureDesktopChrome`).
   - Geometry, grid snapping, and layout calculations (`snapToGrid`, `clampWindowRect`, `computeTileRects`, `computeCascadeRects`, `computeSnapHalf`, `computeTwoColumnsRects`, `computeThreeColumnsRects`, `computeLeftStackedRightFullRects`, `computeLeftFullRightStackedRects`, `computeMaximizeRect`, `computeMobileLayout`).
   - Preferences and local storage persistence (`loadDesktopPrefs`, `saveDesktopPrefs`, `scrubSessionsFromDesktopPrefs`, `collectAgentsFromDom`).
   - Window creation, DOM shell markup, drag handling, resize handling, pointer capture, and state transitions.
   - Dock button rendering, active indicator syncing, horizontal scrolling.
   - Layout presets (tile, cascade, split columns, stack, custom saved layouts) and organize popup menu.
   - Keyboard shortcut handling and clock ticking.
2. Numerous existing frontend test suites import these helpers directly (`tests/unit/frontend/agent_desktop.test.js`, `desktop_canvas_presets_279.test.js`, `desktop_organize_zorder_297.test.js`, `desktop_window_layout.test.js`, `routines_modal_zorder_dock_clearance_344.test.js`, etc.).

---

## 3. What Will Change (Beat 3)

Decompose `src/web/static/modules/ui/agent-desktop.js` into 6 single-responsibility submodules under `src/web/static/modules/ui/agent_desktop/`:

1. **`layout.js`** (~320 lines):
   - Grid constants (`GRID_SIZE`, `DESKTOP_DOCK_Z`, `DESKTOP_MODAL_Z`, `DESKTOP_WINDOW_Z_CAP`, `nextDesktopStackZ`).
   - Pure geometry calculations (`cascadeOffset`, `snapToGrid`, `snapRectToGrid`, `clampWindowRect`, `computeTileRects`, `computeCascadeRects`, `computeSnapHalf`, `computeTwoColumnsRects`, `computeThreeColumnsRects`, `computeLeftStackedRightFullRects`, `computeLeftFullRightStackedRects`, `computeMaximizeRect`, `computeMobileLayout`).
2. **`prefs.js`** (~110 lines):
   - Storage constants and sanitizers (`PREFS_KEY`, `scrubSessionsFromDesktopPrefs`, `collectAgentsFromDom`).
   - Persistence routines (`loadDesktopPrefs`, `saveDesktopPrefs`).
3. **`chrome.js`** (~150 lines):
   - `DOCK_LAUNCHERS` manifest configuration.
   - `ensureDesktopChrome()`: DOM creation of dock, window layer, clock, organize menu, and grid overlay.
   - Dialog host z-index enhancement (`enhanceHitlDialogs`).
4. **`dock.js`** (~160 lines):
   - Dock item rendering (`renderDock`), active state updating (`updateDockActive`), scroll indicators (`updateDockScrollChrome`, `scrollDockBy`, `bindDockScroll`).
5. **`presets.js`** (~280 lines):
   - Builtin arrange presets (`arrangePreset`, tile, cascade, 2-col, 3-col, left/right stacked).
   - Saved custom layouts (`promptSaveCurrentLayout`, `applyPreset`, `deletePreset`).
   - Organize dropdown menu rendering and event bindings (`renderOrganizeMenuContent`, `bindOrganizeMenu`).
6. **`window.js`** (~480 lines):
   - Window shell instantiation (`createWindowShell`).
   - Pointer drag and resize controllers (`bindWindowChrome`, title drag, resize borders, pointer capture, grid snapping).
   - Window lifecycle controls (`applyRect`, `focusWindow`, `openWindow`, `minimizeWindow`, `closeWindow`, `toggleMaximize`, `applyMobileLayout`).
7. **Root Coordinator `agent-desktop.js`** (~250 lines):
   - Coordinates initialization (`initAgentDesktop`), sets up global key shortcuts (Alt+1..9, Esc), manages live agent ticker timer, and re-exports all decomposed submodule functions and constants for 100% backward compatibility.
8. **Contract Test Suite**:
   - `tests/unit/frontend/desktop_monolith_decomposition_403.test.js`: Verifies line counts (<800 for submodules, <1000 for root coordinator) and tests exported symbols.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Delete monolithic 1,894-line file structure in `src/web/static/modules/ui/agent-desktop.js`.
- Delete duplicate inner scope geometry calculations and inline DOM templates scattered across `agent-desktop.js`.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-403-001] Submodule Line Size Caps**:
  - *The System Shall* enforce that every submodule under `src/web/static/modules/ui/agent_desktop/*.js` contains fewer than 800 lines of code, and the root coordinator `agent-desktop.js` contains fewer than 1,000 lines of code.

- **[REQ-403-002] Backward Compatible Public API Re-exports**:
  - *The System Shall* re-export all public symbols and constants (`DOCK_LAUNCHERS`, `GRID_SIZE`, `DESKTOP_DOCK_Z`, `DESKTOP_MODAL_Z`, `DESKTOP_WINDOW_Z_CAP`, `nextDesktopStackZ`, `PREFS_KEY`, `scrubSessionsFromDesktopPrefs`, `cascadeOffset`, `snapToGrid`, `snapRectToGrid`, `clampWindowRect`, `computeTileRects`, `computeCascadeRects`, `computeSnapHalf`, `computeTwoColumnsRects`, `computeThreeColumnsRects`, `computeLeftStackedRightFullRects`, `computeLeftFullRightStackedRects`, `computeMaximizeRect`, `computeMobileLayout`, `collectAgentsFromDom`, `loadDesktopPrefs`, `saveDesktopPrefs`, `initAgentDesktop`) directly from `src/web/static/modules/ui/agent-desktop.js`.

- **[REQ-403-003] Window Manager & Layout Fidelity**:
  - *When* windows are opened, dragged, resized, minimized, maximized, or arranged with canvas presets,
  - *The System Shall* execute identical state transitions, z-stack ordering, grid snapping, and DOM updates without functional regression.

- **[REQ-403-004] Dock & Organize Menu Fidelity**:
  - *When* users interact with the dock, scroll buttons, launcher icons, or the organize menu,
  - *The System Shall* update dock indicators and execute organize actions identically to the legacy implementation.

- **[REQ-403-005] Negative Assertion Against Regressions**:
  - *The System Shall* fail automated contract test `tests/unit/frontend/desktop_monolith_decomposition_403.test.js` if any submodule exceeds 800 lines, if `agent-desktop.js` exceeds 1,000 lines, or if any public exported symbol is missing.

---

## 6. Constraints & Verification Plan

- Feature branch `feat/CARD-403-desktop-monolith-decomposition` cut from `qa`.
- Submodule file size constraints: `agent-desktop.js` < 1,000 lines, all submodules < 800 lines.
- Vitest suite `npm run test:unit:frontend` and linting `npm run lint:frontend` must pass 100% green.
- Verify existing desktop tests: `agent_desktop.test.js`, `desktop_canvas_presets_279.test.js`, `desktop_window_layout.test.js`, etc.

---

## Triage closure (2026-09-23)

Marked **Done** on `qa` tip `97c22bd6`. Acceptance evidence:

- Root coordinator `src/web/static/modules/ui/agent-desktop.js`: **698** lines (`split('\n')`; < 1,000).
- Submodules under `src/web/static/modules/ui/agent_desktop/` all < 800: `agent_hydration.js` 30, `chrome.js` 109, `dock.js` 123, `layout.js` 268, `prefs.js` 122, `presets.js` 420, `window.js` 777.
- Contract suite present: `tests/unit/frontend/desktop_monolith_decomposition_403.test.js` (line caps + export checks).
- CHANGELOG already records the decomposition and re-exports under [CARD-403].

No follow-up Ready card needed; size-cap criteria are met.
