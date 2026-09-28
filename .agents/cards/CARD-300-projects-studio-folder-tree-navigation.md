# [CARD-300] Projects Studio folder tree navigation

> **Status**: Done  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: scratch/jacobs-walk-braindump.txt
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
PROJECTS_ROOT navigable folder tree like Wiki for picking default project root instead of a huge flat list.

---

## 2. What to Build
Up/back + folder-only tree under PROJECTS_ROOT; set default from tree selection.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `/api/projects/browse` folder-only under projects_root
- [x] Up/Root chrome + Set Active from tree
- [x] Vitest + pytest green for CARD-300

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Design lock (UI/UX — marathon)
- Folder-only tree under `PROJECTS_ROOT` with up/back; set default from tree selection.


## Live proof (2026-09-13)

- Tip 49af63d served on Jarvis :8000. HTTP contract green. See scratch/SUPER-MARATHON-295-300-proof.md.
