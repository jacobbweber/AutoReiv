---
id: CARD-624
title: "Toasts appear underneath the desktop dock, so you cannot see them (desktop and phone)"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-624-toast-visible]
  checks: [tests/unit/frontend/toast_above_dock_624.test.js]
branch: feat/card-624-toasts-hidden-under-dock
log: {minutes: 50, qa_runs: 1, findings: 0}
created: 2026-10-03
completed: 2026-10-05
related:
  - CARD-471
  - CARD-396
---

# CARD-624 Toasts appear underneath the desktop dock, so you cannot see them (desktop and phone)

> **Status**: Done (2026-10-05, merged to qa from `feat/card-624-toasts-hidden-under-dock`).

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
| card-624-toast-visible | desktop | PASS | hit-test + above dock band |
| card-624-toast-visible | phone | PASS | same |
Screenshots: `sprint1005\624-toast-above-dock-desktop.png`, `624-toast-above-dock-phone.png`.

## Built
- `#toastContainer` z-index 11000 (dock 10000); `bottom: calc(6rem + safe-area)`.
- `toast.js` + `index.html` classes; `desktop.css` hard rule; cache `desktop.css?v=2.0.83`, `app.js?v=2.0.112`.
- Vitest (2), smoke TC-53 (Save to Wiki empty-thread toast), journey.

## Tests
- Pytest 2533/12; vitest 1062; smoke 85; release preflight GREEN.
- Live QA Spark: desktop+phone PASS.

## Release note
Notifications show above the dock instead of hiding behind it.
