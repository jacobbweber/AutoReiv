# [CARD-296] Chat picker sessions drawer and jump to latest

> **Status**: Ready  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: docs/cards/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Chat chrome: one agent picker (left, show-in-chat); sessions as in-studio drawer not desktop window; smart autoscroll + Jump to latest.

---

## 2. What to Build
Remove Chat top-right agent dropdown; sessions left drawer with New Conversation + recent only, select loads and auto-collapses; implement autoscroll/Jump to latest.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Done bar (anti-theatre)

1. Chat Studio shows **one** agent picker (left) that honors Agent Studio **Show in Chat**; top-right Chat agent dropdown is gone.
2. Sessions control opens an **in-studio** left drawer (not a separate desktop window): New Conversation + recent chats only — **no** Active Agent picker in the drawer.
3. Selecting a recent chat loads it and **auto-collapses** the drawer.
4. Smart autoscroll while streaming + visible **Jump to latest** when the operator scrolls up.
5. Live smoke on Jarvis (Ctrl+F5) covering picker, drawer, and jump control.

