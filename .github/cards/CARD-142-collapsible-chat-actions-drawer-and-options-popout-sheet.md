# [CARD-142] Collapsible Chat Actions Drawer and Options Popout Sheet

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
The mobile chat input container currently displays multiple runtime mode checkboxes (`Verify`, `Goal`, `Auto-run`) and a workflow dropdown permanently inside the input card. This occupies 2+ vertical lines on phones, cluttering the bottom bar and reducing visible message history. The user wants to collapse these options into an expandable drawer/popout button (`[ + ]` / Options) that tucks the controls away when not needed, while establishing the foundation for upcoming file attachments and prompt catalog tools.

---

## 2. What to Build

### A. Sleek Compact Input Dock
- When closed, the input card displays only:
  - The typing textarea (`#chatInput`).
  - Left: An ergonomic **Chat Actions Button** (`#chatOptionsToggleBtn`) with `[ + ]` icon and active mode indicator badge (`#chatActiveModesIndicator`).
  - Right: Send/Stop button (`#sendBtn` / `#stopBtn`).
- Height reduction: Reclaims over 50px of vertical chat height on mobile and desktop.

### B. Collapsible Options Popout Drawer (`#chatOptionsDrawer`)
- Tapping `#chatOptionsToggleBtn` smoothly slides open `#chatOptionsDrawer` directly above the input textarea.
- Drawer Header:
  - Left: `⚙️ Chat Modes & Options`
  - Right: `[ ✕ ]` Close button (`#chatOptionsCloseBtn`).
- Drawer Sections:
  1. **Runtime Modes Grid**:
     - `Verify` toggle (`#verifyToggle`)
     - `Goal` toggle (`#goalToggle`)
     - `Auto-run` toggle (`#approvalToggle`)
  2. **Workflow Runner**:
     - Workflow selector (`#workflowPicker`) and Save button (`#saveAsWorkflowBtn`).
  3. **Action Shortcuts Placeholder** (Foundations for Slices 2 & 3):
     - `[ 📎 Attach File ]` (Disabled pill indicating Slice 2)
     - `[ 📚 Prompt Catalog ]` (Disabled pill indicating Slice 3)
- Pressing `Escape` or tapping outside/the close button closes the drawer.

---

## 3. Wireframes

### Closed State (Super Sleek & Compact)
```text
+-------------------------------------------------------------+
| Type a message or instruction...                            |
|                                                             |
| [ + ] [🎯 Goal Active]                                  [ ✈️ ]|
+-------------------------------------------------------------+
```

### Expanded Options Drawer
```text
+-------------------------------------------------------------+
| ⚙️ Chat Modes & Options                                  [ ✕ ]|
+-------------------------------------------------------------+
| RUNTIME MODES:                                              |
| [ ✓ Verify ]       [ 🎯 Goal Mode ]       [ ⚡ Auto-run ]    |
|                                                             |
| WORKFLOW SELECTOR:                                          |
| [ 🔄 Select a workflow...                         v ]       |
|                                                             |
| ACTIONS:                                                    |
| [ 📎 Attach File (Slice 2) ]     [ 📚 Prompt Catalog (Slice 3) ]|
+-------------------------------------------------------------+
| Type a message or instruction...                            |
| [ ✕ ]                                                   [ ✈️ ]|
+-------------------------------------------------------------+
```

---

## 4. Acceptance Criteria (EARS & DoD)
- [ ] `[REQ-CHAT-DRAWER-001]`: The chat form must default to a compact state with mode checkboxes and workflow controls collapsed inside `#chatOptionsDrawer`.
- [ ] `[REQ-CHAT-DRAWER-002]`: Tapping `#chatOptionsToggleBtn` toggles visibility of `#chatOptionsDrawer` with smooth animation and accessibility attributes (`aria-expanded`, `aria-controls`).
- [ ] `[REQ-CHAT-DRAWER-003]`: Active modes must be visually indicated on `#chatOptionsToggleBtn` via `#chatActiveModesIndicator` so users know at a glance when Goal, Verify, or Auto-run are engaged.
- [ ] `[REQ-CHAT-DRAWER-004]`: All existing control IDs (`#verifyToggle`, `#goalToggle`, `#approvalToggle`, `#workflowPicker`, `#sendBtn`, `#stopBtn`) are preserved with exact behavior parity.
- [ ] `[REQ-CHAT-DRAWER-005]`: Automated unit tests verify drawer toggle state, keyboard interactions, and active indicator badge synchronization.
- [ ] Automated tests green via `npm run test:unit:frontend` and `pytest tests/unit/web`.
- [ ] Zero lint errors via `npm run lint:frontend`.
