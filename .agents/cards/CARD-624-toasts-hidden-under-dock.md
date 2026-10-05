---
id: CARD-624
title: "Toasts appear underneath the desktop dock, so you cannot see them (desktop and phone)"
type: bug
status: In Progress
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-624-toast-visible]
  checks: [tests/unit/frontend/toast_above_dock_624.test.js]
branch: feat/card-624-toasts-hidden-under-dock
log: {minutes: 15, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-471
  - CARD-396
---

# CARD-624 Toasts appear underneath the desktop dock, so you cannot see them (desktop and phone)

## Problem
In the CARD-471 live check (2026-10-03, :8770), every toast rendered behind the dock bar. On desktop (1024x640) the toast box sat at y 572-624 and `elementFromPoint` at its centre returned a `.desktop-dock-icon`. On phone (390x844) it sat at y 776-828 and returned `#desktopDockApps`. The text is in the DOM, so tests pass, but you cannot see the message (for example, the Compact result in `desktop-07-toast-under-dock.png` / `phone-07-toast-under-dock.png` in `autoreiv-qa\ui1003i`).

## Cause
`#toastContainer` (index.html L4453, `modules/ui/toast.js`) is `fixed bottom-4 right-4 z-50`. `.desktop-dock` in `src/web/static/css/desktop.css` (L455) has `z-index: 10000` and covers the bottom of the screen.

## Change
- Place the toast stack above the dock (raise its z-index above the dock and offset it by the dock height on the agent desktop, including the phone layout). Add a smoke or live check that a toast's centre hit-tests to the toast.

## What dies
Messages nobody can read.

## Proof
- Journey `card-624-toast-visible`: trigger a toast on desktop and phone; `elementFromPoint` at its centre is inside the toast and the screenshot shows it above the dock.

## Plan and decisions
- Raise `#toastContainer` to `z-index: 11000` (dock is 10000) and set `bottom: calc(4.75rem + safe-area)` so the stack clears the dock band on desktop and phone.
- Same classes in `toast.js` + `index.html`; CSS rule in `desktop.css` as the hard floor.
- Vitest + smoke TC-53 + journey `card-624-toast-visible`.

## Findings
- (from the CARD-471/473 live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Notifications show above the dock instead of hiding behind it.
