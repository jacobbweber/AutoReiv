# [CARD-207] Desktop Window Resize, Scrollable Studios, and Sessions Cleanup

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:ui`, `domain:desktop`, `domain:ux`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Sessions Window Cleanup**:
   - When clicking the Sessions button in the bottom dock (`#dock-sessions`), the window should show chat sessions without the redundant "All Studios" navigation grid at the bottom, since all studios already live on the bottom dock (`#desktopDock`).
   - Removing "All Studios" allows the chat sessions list (`#sessionList`) to expand vertically so the user can see all their recent conversations.
   - The Sessions window must be resizable just like any other window.
2. **Page Scrolling in Studios (Settings, Routines, Observe)**:
   - When opening Settings (`#view-settings`), Routines (`#view-routines`), or Observe (`#view-observability`), the content must not be cut off.
   - The user must be able to scroll up and down through the full page content on both desktop windows and mobile screens.
3. **Bottom-Right Corner Drag and Resize on Every Window**:
   - Every single floating window (Chat, Wiki, Projects, Agents, Factory, Routines, Observe, Settings, Prompts, Sessions) must have a functional bottom-right corner drag handle (`.desktop-win-resize-se`).
   - Dragging the bottom-right corner must smoothly resize the window's width and height.

---

### Beat 2: What AutoReiv Does Now
1. **Redundant "All Studios" in Sessions Window**:
   - `#sidebarNav` ("All Studios" grid of 9 buttons) is rendered inside `#sidebar` in `src/web/templates/index.html`.
   - When `#sidebar` is displayed inside the desktop Sessions window, `#sidebarNav` takes up over 200px of vertical space, compressing `#sessionList` down to a tiny area.
2. **Page Scrolling Blocked by Global Desktop View Rule**:
   - In `src/web/templates/index.html` (line 221), `.tab-view.desktop-view-hosted` has `overflow: hidden !important;`.
   - This rule overrides `overflow-y-auto` on `#view-settings`, `#view-routines`, and `#view-observability`, cutting off content below the window fold with no scrollbar.
3. **Resize Handles Covered by Hosted Views & Sidebar**:
   - The window shell (`.desktop-window`) has `z-index: win.z`.
   - The hosted view (`.desktop-view-hosted`) is positioned over the window at `z-index: win.z + 1`.
   - `#sidebar` has hardcoded `z-index: 50 !important;`.
   - Because the hosted view sits on top of the window frame, the bottom-right resize handle (`.desktop-win-resize-se`) is underneath the content layer. Clicks and drag gestures hit the content pane instead of the resize handle.

---

### Beat 3: What Will Change
1. **Remove "All Studios" from Desktop Sessions Window**:
   - In `src/web/templates/index.html`, hide `#sidebarNav` when `#sidebar` is hosted in desktop mode (`body.radical-desktop-demo.desktop-sessions-open #sidebarNav { display: none !important; }`).
   - Allow `#sessionList` to take full available vertical height inside `#sidebarChatSection`.
2. **Restore Vertical Scrolling to Studio Windows**:
   - Update `.tab-view.desktop-view-hosted` CSS so page-style views (`#view-settings`, `#view-routines`, `#view-observability`, and any `.tab-view.overflow-y-auto`) have `overflow-y: auto !important;` with smooth scrolling.
   - Maintain full scrollability on mobile screens where windows fill the viewport above the dock.
3. **Elevate Bottom-Right Corner Resize Handle Above Content**:
   - In `src/web/templates/index.html` and `src/web/static/modules/ui/agent-desktop.js`, ensure `.desktop-win-resize` handles (especially `.desktop-win-resize-se`) have a stacking index higher than the hosted views (`z-index: 30` inside the window or elevated to `win.z + 2`).
   - Ensure `#sidebar` uses the window's dynamic coordinates without a hardcoded `z-index: 50 !important;` so the Sessions window's resize handle is exposed and functional.
   - Ensure the visible diagonal grip on `.desktop-win-resize-se` renders clearly in the bottom-right corner of every window.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1 (Sessions Window Cleanup)**:
  - In desktop mode, clicking the Sessions dock icon opens the Sessions window without the "All Studios" button grid (`#sidebarNav` is hidden).
  - `#sessionList` expands to use the freed vertical space and scrolls through all recent chat sessions.
- [x] **AC-2 (Studio Page Scrolling on Desktop & Mobile)**:
  - Settings (`#view-settings`), Routines (`#view-routines`), and Observability (`#view-observability`) allow vertical scrolling through all sections.
  - Page contents are not cut off.
  - Mobile viewports also scroll smoothly through all studio contents.
- [x] **AC-3 (Bottom-Right Drag Resize on Every Window)**:
  - Every floating window (Chat, Wiki, Projects, Agents, Factory, Routines, Observe, Settings, Prompts, Sessions) has a visible bottom-right corner grip.
  - Clicking and dragging the bottom-right corner smoothly resizes both width and height on desktop.
- [x] **AC-4 (Automated Tests)**:
  - Unit tests in Vitest verify DOM layout rules and CSS class behavior.
  - Playwright smoke tests pass cleanly (`npm run test:smoke`).
  - Full preflight passes: `python .agents/skills/rtm-sync/scripts/preflight.py`.

---

## 3. Constraints & Invariants
- Follows "How we walk cards with Jacob" in `AGENTS.md`.
- No implementation code written until Jacob approves this card with "build".
- Local `qa` branch workflow. Zero push, tag, or merge to `main`.
