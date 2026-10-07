---
id: CARD-658
title: "1.0 gate — Windows service install keeps user data through uninstall and reinstall"
type: feature
status: Ready
priority: P1
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
related:
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-658 1.0 gate — Windows service install keeps user data through uninstall and reinstall

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
Before calling AutoReiv 1.0 on Windows, prove that installing as a Windows service, using the product, uninstalling, and installing again never deletes the operator's data folder, and that the reinstall finds the same data.

## Goal
An operator on Windows can install AutoReiv as a service, send a real chat message, uninstall the service, confirm the user data folder is still there and unchanged, then reinstall and see the same chat (or the same data) still present. The expected Windows data path is written down on the card and in the install docs (CARD-668).

## Acceptance
- Install as a Windows service on a clean machine (or a clean data folder).
- Run one real chat turn that is saved.
- Uninstall the service.
- Confirm the user data folder was not deleted or wiped (path documented; expected default under the Windows Local AppData AutoReiv folder unless overridden).
- Reinstall; the earlier chat (or equivalent saved data) is still there.
- Document the expected Windows data path in this card's Results and in CARD-668.

## Plan and decisions
Needs Jacob's build approval before any work starts. Prefer a scripted check that can run on Jarvis without touching the live day-to-day data folder (use a throwaway data path if the installer allows it).
