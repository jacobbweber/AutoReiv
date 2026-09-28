---
id: CARD-410
title: "Fix Browser Refresh Empty Agent Picker in Pre-Opened Studio Windows"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:bug
  - area:ux
  - area:studios
---

# [CARD-410] Fix Browser Refresh Empty Agent Picker in Pre-Opened Studio Windows

> **Status**: Done
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

Confirmed on `qa` before the fix:

1. **Agent Studio misses the restore tick**:
   `forge.js` is loaded with a dynamic `import()`. `initAgentDesktop` restores `localStorage` `openWindows` synchronously and calls `switchTab('agents')` while `forgeCtrl` is still null, so `loadAgentForge()` does not run. When the module arrives, `initAgentForge()` does not load the roster. `#forgeAgentSelect` stays empty until a later tab switch (close the window and open it from the dock).
2. **One-shot picker fills**:
   Chat, Factory, Routines, and Observe each wrote their `<select>` inside their own `/api/agents` fetch. Nothing published `agents:loaded`, and a subscriber that mounted after the response (Agent Studio) was not replayed.
3. **Forge selection was not stored**:
   Chat already kept `autoreiv_active_agent_id`. Agent Studio, Factory, the Routines filter, and the Observe KPI filter did not, so a reload could not put the prior agent back.
4. **Dock reopen workaround**:
   Opening the studio again calls `switchTab` after `forgeCtrl` exists, so the picker finally fills.

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

### Automated proof
- `tests/unit/frontend/agent_picker_refresh_410.test.js` — pickers stay empty until `agents:loaded`, then Chat / Agent Studio / Factory / Routines / Observe options appear with the stored agent selected. A subscriber that attaches after the roster is already in memory still fills `#forgeAgentSelect` (the dynamic-import race). Negative: no options before the event, and `assistant` / `wiki` / `agent-builder` stay out of the Agent Studio and Chat pickers.
- `tests/unit/frontend/agent_desktop.test.js` — a restored `agents` window runs the hydration callback once; the picker fills when the roster arrives, without creating a second window. Dock launch calls the same hydration hook.

Operator contracts (OC-1..OC-3) are not the lock for this bug. It is an in-browser window restore race, not a settings write, wiki inbox note, or observe report. No new OC row.

### Manual verification (Jacob)
1. Start AutoReiv and open the desktop (`/` on the serve port).
2. From the dock, open **Agents** (Agent Studio) and **Chat**. Optionally also open Factory, Routines, and Observe.
3. In Chat and in Agent Studio, choose an agent (for example `AutoReiv`, or another agent if you want to prove it is not just the first row).
4. Press `F5` or `Ctrl+F5`.
5. Expect: those windows are back, each agent dropdown lists the roster, and the agent you chose is still selected. Do not close or reopen the windows.
6. Expect the same after a dock click on a studio that was already open: the picker stays populated. It must not be the only way to get options.
