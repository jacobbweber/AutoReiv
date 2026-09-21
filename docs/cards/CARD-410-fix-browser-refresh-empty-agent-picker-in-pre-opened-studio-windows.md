---
id: CARD-410
title: "Fix Browser Refresh Empty Agent Picker in Pre-Opened Studio Windows"
status: Ready
created: 2026-09-21
adr: none
labels:
  - type:bug
  - area:ux
  - area:studios
---

# [CARD-410] Fix Browser Refresh Empty Agent Picker in Pre-Opened Studio Windows

> **Status**: Ready  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:bug`, `area:ux`, `area:studios`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

When Jacob refreshes his browser (F5 / Ctrl+F5) while Agent Studio (Forge) or other studios are already open as active windows on the Agent Desktop, the agent dropdown selector is empty or null.

Jacob is forced to close the open studio window and reopen it from the desktop dock launcher before the agent roster populates again.

**Goal**: On browser refresh or page reload, any studio window restored from desktop layout state must automatically and reliably populate its agent dropdown pickers without requiring the operator to close and reopen the window.

---

## 2. What AutoReiv Does Now (Beat 2: Current Behavior & Root Cause)

1. **Window Hydration Race**:
   On page load, `agent_desktop/prefs.js` and `agent-desktop.js` restore open windows from `localStorage` (`openTabs` / window states).
2. **Asynchronous Roster Fetch Delay**:
   The `/api/agents` catalog fetch in `app.js` runs asynchronously in parallel.
3. **Missing Re-Population Trigger**:
   When restored studio DOM elements mount, the agent roster is not yet available in the global store or the studio's local cache. Once `/api/agents` resolves, pre-rendered `<select>` elements in already-opened windows are not refreshed or notified to re-populate their options.
4. **Dock Reopen Workaround**:
   Clicking the dock launcher triggers a fresh studio open flow, which re-reads the now-cached agent roster and populates the picker, creating the impression that a window close/reopen cycle is required.

---

## 3. What Will Change (Beat 3: Technical Implementation)

1. **Event-Driven Roster Broadcast (`eventBus`)**:
   - When `/api/agents` resolves in `app.js` or `store.js`, publish an event on the shared event bus: `agents:loaded` (with the fetched agent list).
2. **Studio Dropdown Subscriptions**:
   - `forge.js`: Subscribe to `agents:loaded`. If the Agent Studio window DOM exists, re-populate the agent dropdown `<select>` and preserve the previously active selection.
   - `chat.js`, `routines.js`, `observability.js`, `factory.js`: Ensure all agent pickers subscribe to `agents:loaded` and re-render options dynamically.
3. **Window Mount Hydration Hook**:
   - In `agent_desktop/window.js` and `dock.js`, when a window is restored from saved desktop state, verify if the store already has `agents`. If populated, immediately bind the options; if still loading, bind a one-time promise/listener to populate as soon as the fetch completes.

---

## 4. What Dies Today (Beat 4: The Prune List)

- **PRUNE**: One-shot synchronous assumption in studio agent picker population routines.
- **PRUNE**: The manual operator workaround requiring closing and reopening windows to recover populated pickers.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-410-001] Page Refresh Roster Persistence**:
  - *Event-Driven*: WHEN the operator refreshes the browser with Agent Studio or any agent-dependent studio window already open, THE SYSTEM SHALL restore the window with the agent dropdown picker fully populated with all available agents.
- **[REQ-410-002] Active Selection Preservation**:
  - *Ubiquitous*: THE SYSTEM SHALL retain the currently selected agent in the restored window upon page reload, matching the prior session state if valid.
- **[REQ-410-003] Zero Window Destroy Requirement**:
  - *Ubiquitous*: THE SYSTEM SHALL NOT require the operator to close and reopen any desktop window to see the populated agent roster.

---

## 6. Constraints & Verification Plan

### Automated Tests
- Vitest unit test in `tests/unit/frontend/`: Simulate window hydration from localStorage before `/api/agents` resolves, trigger `agents:loaded` event, and assert `<select>` element contains expected option elements.
- Vitest test in `tests/unit/frontend/agent_desktop.test.js`: Verify restored window callbacks correctly trigger studio agent binding.

### Manual Verification
1. Open Agent Studio (Forge) and Chat Studio on the desktop.
2. Select an agent (e.g. `AutoReiv`).
3. Press `F5` / `Ctrl+F5` to reload the page.
4. Verify: Both windows restore with populated agent dropdowns and `AutoReiv` selected. Zero need to close and reopen the windows.
