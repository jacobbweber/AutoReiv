---
id: CARD-279
title: "UI — Pin / Save Studio Layouts & Canvas Presets"
status: Done
created: 2026-09-13
completed: 2026-09-19
adr: none
labels:
  - type:feature
  - ui
  - desktop
  - layout
  - presets
---

# [CARD-279] UI — Pin / Save Studio Layouts & Canvas Presets

> **Status**: Done  
> **Created**: 2026-09-13  
> **Completed**: 2026-09-19  
> **Labels**: `type:feature`, `ui`, `desktop`, `layout`, `presets`  
> **Branch**: `feat/card-279-pin-save-studio-layouts` off `qa`  


---

## 1. The Four Beats

### Beat 1: What Jacob Means
1. **Multi-Window Canvas Presets**: Provide intuitive, ergonomic window layout presets in the desktop dock's Organize menu beyond just "snap left/right". Specifically, support a **3-window layout** (e.g. Left stacked: two 50% height windows + Right full: one 100% height window, matching Jacob's screenshot: Chat top-left, Agents bottom-left, Wiki right), an inverted 3-window layout (Left full + Right stacked), 2-column 50/50 split, 3-column equal split, tile, and cascade.
2. **Save & Pin Custom Layout Presets**: Allow operators directly within the Organize menu to **"Save Current Layout"** (capturing which studios are open, their exact coordinates/dimensions `x, y, w, h`, and stacking order), name or manage saved layout presets, and load them with one click.
3. **Sticky Session Persistence & Auto-Restore on Boot**: When an operator reloads or returns to AutoReiv on desktop, the canvas automatically restores the exact studios that were open and their positions rather than resetting to a single window or blank canvas.
4. **Desktop-Only Scope**: Multi-window tiling and custom layouts apply exclusively to desktop viewport widths (>=768px). Mobile continues to enforce the focused single-window mobile layout.

### Beat 2: What AutoReiv Does Now
1. In `src/web/static/modules/ui/agent-desktop.js`:
   - The dock Organize button (`#desktopOrganizeBtn`) opens a flat menu with only 6 basic actions: `Tile all`, `Cascade`, `Snap left half`, `Snap right half`, `Maximize / restore`, and `Toggle grid overlay`.
   - There are no 3-window layout presets (left-stacked / right-full or vice-versa).
   - Layout preferences in `localStorage` (`autoreiv_desktop_prefs_v1`) only record the last-known rectangle for previously opened windows, but **never record which windows are currently open** or provide any mechanism to save, name, pin, or recall custom layout configurations.
   - On page refresh, no open windows are restored automatically; the canvas starts with all views parked until a user explicitly clicks dock launchers.

### Beat 3: What Will Change
1. **Pure Canvas Presets Geometry Engine** (`agent-desktop.js`):
   - `computeLeftStackedRightFullRects(viewport)`: Rectangles for 3 windows — window 0 top-left (50% w, 50% h), window 1 bottom-left (50% w, 50% h), window 2 right (50% w, 100% h).
   - `computeLeftFullRightStackedRects(viewport)`: Rectangles for 3 windows — window 0 left (50% w, 100% h), window 1 top-right (50% w, 50% h), window 2 bottom-right (50% w, 50% h).
   - `computeTwoColumnsRects(viewport)`: Side-by-side 50/50 split.
   - `computeThreeColumnsRects(viewport)`: 3 equal vertical columns (33.3% w each, 100% h).
   - Smart window assignment: If fewer than 3 windows are currently open when triggering a 3-window preset, gracefully populate the remaining slot(s) from recent/priority launchers (`chat` -> `wiki` -> `agents` -> `projects`) without crashing.
2. **Organize Menu Restructuring & Visual Hierarchy** (`index.html`, `agent-desktop.js`):
   - Group the Organize menu into 3 clean, accessible sections with dividers:
     - **Canvas Presets**: "3-Window: Left Stacked, Right Full", "3-Window: Left Full, Right Stacked", "Split 50 / 50", "3 Columns Equal", "Tile All", "Cascade".
     - **Window Actions**: "Snap Left", "Snap Right", "Maximize / Restore", "Toggle Grid Overlay".
     - **Saved Layouts**: "Save Current Layout...", "Sticky Auto-Restore on Startup" (toggle), and dynamic list of saved layout presets with "Load" and "Delete" actions.
3. **Layout Preset Storage & Persistence** (`agent-desktop.js`):
   - Extend `loadDesktopPrefs` / `saveDesktopPrefs` schema to include:
     - `openWindows: string[]`: array of open studio tab IDs in stacking order.
     - `autoRestore: boolean`: whether to auto-restore open windows on boot (default true for desktop).
     - `savedPresets: Array<{ id: string, name: string, createdAt: number, windows: Array<{ tab: string, rect: {x, y, w, h}, maximized?: boolean }> }>`.
   - On boot (`initAgentDesktop`), if `autoRestore` is enabled and viewport is desktop (>=768px), automatically restore and position the active open windows cleanly.
4. **Interactive Save Preset Dialog / Prompt**:
   - Provide a quick, non-disruptive modal/prompt asking for an optional preset name (auto-defaulting to open studio names, e.g. "Chat + Agents + Wiki"), saving it immediately into the list.

### Beat 4: What Dies Today (The Prune List)
1. **Flat / Uncategorized Organize Menu**: The hardcoded 6-button flat list in `#desktopOrganizeMenu` is deleted and replaced by categorized sections with presets and saved layouts.
2. **Stateless Boot Blanking**: The behavior where browser refresh drops all open desktop windows into a blank/parked state without restoring open studios is pruned when `autoRestore` is active.
3. **Hardcoded Two-Window Snap Limitation**: The limitation of only being able to snap one window to left or right half is superseded by multi-window canvas presets.

---

## 2. Acceptance Criteria (EARS)

- [x] **[REQ-279-001] (Canvas Presets Math)**: When any canvas preset (`left-stacked-right-full`, `left-full-right-stacked`, `two-columns`, `three-columns`) is invoked with viewport dimensions, the engine SHALL compute non-overlapping, pixel-aligned rectangles conforming to grid boundaries and respecting dock height.
- [x] **[REQ-279-002] (Organize Menu Integration)**: When the operator clicks `#desktopOrganizeBtn`, the Organize dropdown menu SHALL present categorized sections: *Canvas Presets*, *Window Actions*, and *Saved Layouts*.
- [x] **[REQ-279-003] (Three-Window Layout Application)**: When the operator selects the 3-window preset (Left Stacked, Right Full), the engine SHALL layout 3 visible windows such that window 0 occupies the top-left quadrant, window 1 occupies the bottom-left quadrant, and window 2 occupies the right half at 100% height (matching the reference layout). If fewer than 3 windows are open, the engine SHALL open the next highest-priority studio automatically.
- [x] **[REQ-279-004] (Save Current Layout)**: When the operator clicks "Save Current Layout", the engine SHALL prompt for an optional name (defaulting to the names of open studios) and store the preset `{ id, name, createdAt, windows: [...] }` in `localStorage`.
- [x] **[REQ-279-005] (Load & Delete Saved Presets)**: When the operator clicks a saved preset item, the engine SHALL close/park non-member windows and open and size the saved windows to their exact saved coordinates. When the delete button on a preset is clicked, it SHALL be removed from storage.
- [x] **[REQ-279-006] (Session Sticky Auto-Restore)**: When `autoRestore` is true on desktop (>=768px), reloading the application SHALL restore the exact windows and geometries that were active prior to reload.
- [x] **[REQ-279-007] (Mobile Boundary Guard)**: On mobile viewports (<768px), multi-window presets and multi-window auto-restore SHALL be disabled, preserving the single-window mobile layout.
- [x] **[REQ-279-008] (Test-Locked Quality)**: Vitest unit tests in `tests/unit/frontend/desktop_canvas_presets_279.test.js` and `agent_desktop.test.js` SHALL cover all pure geometry functions, storage migrations, preset saving/loading, and edge-case fallbacks with 100% pass rate.

---

## 3. Constraints

- Zero regressions in existing 580 vitest tests and Playwright smoke suites.
- Desktop-only multi-window layouts; mobile (<768px) must never be broken or multi-tiled.
- Stored exclusively in local storage (`localStorage[autoreiv_desktop_prefs_v1]`); no backend DB schema bloat.
- Follow Single Lever Invariant: one canonical organize menu and one canonical window manager engine.

---

## 4. Human QA Runbook

1. Launch AutoReiv: `npm run dev` (or access running server).
2. Open desktop in browser. Click Chat, Agents, and Wiki on the dock.
3. Click the Organize menu icon (`layout-grid` icon on dock).
4. Click **"3-Window: Left Stacked, Right Full"**. Verify Chat is top-left, Agents is bottom-left, and Wiki is right full.
5. In Organize menu, click **"Save Current Layout"**. Enter a name or keep default "Chat + Agents + Wiki".
6. Close Wiki. Open Routines.
7. Re-open Organize menu, click your saved preset. Verify Routines closes/parks, and Chat, Agents, and Wiki return to their exact 3-window positions.
8. Refresh the browser. Verify the 3 windows restore automatically.
