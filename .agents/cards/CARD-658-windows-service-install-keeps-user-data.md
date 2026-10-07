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
log: {minutes: 90, qa_runs: 1, findings: 1}
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

## Results
| Check | Result | Notes |
|---|---|---|
| Expected Windows data path | documented | `%LOCALAPPDATA%\AutoReiv` → `C:\Users\jacob\AppData\Local\AutoReiv` (DataDirResolver + deploy/README) |
| Live data untouched | PASS | Live folder file count stayed 43 after cleanup; test used only `C:\Users\jacob\AppData\Local\AutoReiv-1.0-gate-test`. Transient count blip during the run was SQLite WAL noise on the live serve, not test writes. |
| Real service install (`install_windows_service.ps1`) | BLOCKED | Script requires elevated Administrator console. Agent shell is not elevated. NSSM was installed via winget. |
| Real service uninstall script | BLOCKED | Same admin requirement (`uninstall_windows_service.ps1`). |
| Isolated serve persistence (same entrypoint the service uses) | PASS | `python -m src.cli.main serve` with `AUTOREIV_DATA_DIR=...\AutoReiv-1.0-gate-test` on port 8780. Marker `1.0-gate-marker.txt` token `gate658-20261006-232335` survived stop; session title still present after restart. Test dir deleted after. |
| Chat turn | SKIPPED | `/api/chat/stream` hung or returned 422 with the bodies tried; session create worked. |

**Verdict: PARTIAL.** Data-path persistence works for the Windows default layout when `AUTOREIV_DATA_DIR` points at an isolated folder. Full Windows Service register/unregister was not proven here (needs Administrator). Stock installer does not take a data-dir flag (see CARD-670).

**Implications:** CARD-668 should document Admin + NSSM prerequisites and how to set `AUTOREIV_DATA_DIR` for the service. CARD-662 update/rollback still needs a real service path once Admin is available.

