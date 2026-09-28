# [CARD-297] Desktop Organize Windows always on top

> **Status**: Done  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: scratch/jacobs-walk-braindump.txt
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Organize Windows button must stay above all open studio windows so the operator can always reach it.

---

## 2. What to Build
Raise z-order / stacking for Organize Windows control so it never sits under open windows.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `#desktopDock` z-index is 10000 (above any studio window)
- [x] Window stack capped at 9000 via `nextDesktopStackZ`
- [x] Vitest `desktop_organize_zorder_297.test.js` green
- [x] Organize menu z-index 10001

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Design lock (UI/UX — marathon)
- Organize Windows always highest z-index above open windows.


## Live proof (2026-09-13)

- Tip 49af63d served on Jarvis :8000. HTTP contract green. See scratch/SUPER-MARATHON-295-300-proof.md.
