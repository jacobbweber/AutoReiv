# [CARD-344] Routines Edit Modal Z-Order Stacking and Dock Clearance

> **Status**: Done
> **Created**: 2026-09-17
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:routines`, `domain:desktop`, `domain:ui`, `domain:modal`

---

## 1. Why / Intent

While in Routines Studio on the desktop, clicking "Edit" (or "New Routine") opens a modal that pops up behind the Routines main window frame and extends down behind the bottom desktop dock, cutting off the "Cancel" and "Save Routine" buttons.

### The Three Beats

1. **What Jacob means**:
   When editing or creating a routine in Routines Studio on the desktop:
   - The "Edit Routine" dialog must pop up directly in front of the Routines window and all other desktop windows, never behind the window frame or overlapping titlebar.
   - The dialog must sit cleanly inside the usable desktop workspace, never cut off behind the bottom desktop dock, so that the "Cancel" and "Save Routine" action buttons are always visible, accessible, and never obscured.

2. **What AutoReiv does now**:
   - **Trapped in Window Stacking Context**: In `src/web/templates/index.html` (line 1802), `<div id="routineModal">` is nested *inside* `<section id="view-routines">`. When Routines Studio is hosted in a desktop window, `agent-desktop.js` sets `view.style.zIndex = String(win.z + 1)`. The window frame `win.el` (with the title bar "Routines Schedules") is set to `z-index: String(win.z + 2)`. Because `#routineModal` is a child of `#view-routines`, its stacking level cannot exceed `win.z + 1`, rendering it underneath the window title bar and frame.
   - **Hardcoded Inverted Z-Index**: In `index.html` (lines 879–882), `body.radical-desktop-demo [aria-modal="true"]` has `z-index: 120 !important;`. In Radical Desktop mode, windows scale up to `DESKTOP_WINDOW_Z_CAP = 9000` and the dock is pinned to `DESKTOP_DOCK_Z = 10000`. A z-index of 120 places dialogs far below both focused windows and the dock.
   - **Dock Clipping & Form Scroll Lock**: `#routineModal` uses `fixed inset-0 ... flex items-center justify-center p-4` with an inner card styled as `max-h-[90vh] overflow-y-auto`. Centered in the viewport, 90% of the screen height causes the bottom of the card to plunge directly behind the 64px–72px bottom dock (`#desktopDock`, z-index 10000). Because the action buttons ("Cancel" and "Save Routine") are inside the bottom of the form rather than a pinned footer, scrolling down inside the card still leaves the action buttons concealed behind the dock.

3. **What will change**:
   - **Move `#routineModal` to Document Root**: Relocate `#routineModal` out of `<section id="view-routines">` to the document root alongside other modal dialogs (such as `factoryDeliverableModal`), freeing it from `#view-routines`'s lower window stacking context.
   - **Elevate Desktop Modal Z-Order**: In `src/web/static/modules/ui/agent-desktop.js` and `index.html`, define `export const DESKTOP_MODAL_Z = 11000;` and set `body.radical-desktop-demo .desktop-dialog-host, body.radical-desktop-demo [aria-modal="true"] { z-index: 11000 !important; }`. This guarantees all modal dialogs sit in front of both desktop windows (max 9000) and the desktop dock (10000).
   - **Pin Modal Footer & Add Dock Clearance**:
     - Restructure `#routineModal` into a 3-part layout: pinned header (`flex-shrink-0`), scrollable body (`flex-1 min-h-0 overflow-y-auto`), and pinned footer (`flex-shrink-0 border-t`). The "Cancel" and "Save Routine" buttons will always remain visible at the bottom of the card without needing to scroll to find them.
     - Add dock-aware viewport margin/padding (`max-h-[calc(100vh-6rem)] sm:max-h-[85vh]` and `pb-20 md:pb-24`) so the modal card never extends into or behind the dock.
     - Register `routineModal` in `agent-desktop.js` (`allModals` and `enhanceHitlDialogs`).
   - **Automated Tests**:
     - Add `tests/unit/frontend/routines_modal_zorder_dock_clearance_344.test.js` verifying:
       1. `#routineModal` is not inside `#view-routines`.
       2. Modal CSS z-index is >= `DESKTOP_MODAL_Z` (11000), which exceeds `DESKTOP_DOCK_Z` (10000) and `DESKTOP_WINDOW_Z_CAP` (9000).
       3. `#routineModal` contains a pinned footer with `Cancel` and `Save Routine` buttons outside the scrollable body, with viewport dock clearance.

---

## 2. What to Build

### 1. Template Restructure & Markup (`src/web/templates/index.html`)
- Move `#routineModal` from line ~1802 (`#view-routines`) down to the global dialog section after `</main>` (alongside `factoryDeliverableModal` and `chatToolsModal`).
- Restructure the modal card into:
  - Header with title and close button (`flex-shrink-0`).
  - Scrollable form body (`flex-1 min-h-0 overflow-y-auto overscroll-contain`).
  - Pinned footer with Cancel and Save buttons (`flex-shrink-0 border-t border-white/[0.06] bg-[#0e1015]`).
- Add container dock clearance (`pb-20 md:pb-24` and `max-h-[calc(100vh-6.5rem)]`).

### 2. Desktop Layering & Z-Order Constants (`agent-desktop.js` & `index.html`)
- In `src/web/static/modules/ui/agent-desktop.js`:
  - Export `export const DESKTOP_MODAL_Z = 11000;`.
  - Include `routineModal` in `enhanceHitlDialogs()`.
- In `src/web/templates/index.html`:
  - Update `.desktop-dialog-host, [aria-modal="true"]` rule to `z-index: 11000 !important;`.

### 3. Studio JavaScript Binding Check (`routines.js`)
- Verify that element lookup `$('routineModal')`, `$('routineModalForm')`, etc., in `src/web/static/modules/studios/routines.js` continue to bind cleanly by ID without assuming DOM parentage.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `#routineModal` is located at the document root outside `<section id="view-routines">`.
- [x] In Radical Desktop mode, `#routineModal` opens in front of the Routines window and all other desktop windows (`z-index: 11000` > `DESKTOP_WINDOW_Z_CAP: 9000`).
- [x] In Radical Desktop mode, `#routineModal` and its action buttons sit in front of and clear of the bottom desktop dock (`z-index: 11000` > `DESKTOP_DOCK_Z: 10000`).
- [x] The "Cancel" and "Save Routine" buttons are pinned in a non-scrolling modal footer (`flex-shrink-0`) and remain visible at all times regardless of form body scroll position.
- [x] Creating a new routine or editing an existing routine saves successfully, closes the modal, and updates the routine card in the grid.
- [x] Pressing `Escape` or clicking the close button dismisses the modal without error.
- [x] Automated frontend unit tests pass (`npm run test:unit:frontend`).
- [x] Zero lint errors (`ruff check .`, `npm run lint:frontend`).

---

## 4. Constraints & Honor Flags

- Zero remote push (`git push` strictly forbidden).
- No code changes before Jacob gives the explicit command `build`.
- Isolated `feat/CARD-344-routines-edit-modal-z-order` branch cut from `qa`.

