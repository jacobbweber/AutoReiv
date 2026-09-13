# [CARD-298] Wiki Studio tighten labels meta and curate honesty

> **Status**: In Review  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: scratch/jacobs-walk-braindump.txt
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Single identity as Wiki-based Document Repository; drop duplicate Expand keep Meta; confirm Curate Inbox is real agent review not theatre.

---

## 2. What to Build
Rename/describe Wiki Studio consistently; remove Expand keep Meta; audit Curate Inbox loop and prove reasoning or label honestly if sync-only.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Wiki header = Wiki / Wiki-based Document Repository
- [x] Meta kept; Expand indicator removed
- [x] Curate Inbox → Graduate Inbox with rule-based honesty
- [x] Vitest `wiki_studio_tighten_298.test.js` green

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Design lock (UI/UX — marathon)
- Single Wiki name/description (Wiki-based Document Repository).
- Drop Expand; keep Meta.
- Curate Inbox must prove real review **or** honest “fast move” label (no theatre).
