# [CARD-301] Chat remove desktop titlebar agent picker

> **Status**: In Review  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: Jacob review fix #1 + Architect lock
> **Labels**: `type:bugfix`, `needs-triage`

---

## 1. Why / Intent
Jacob review: Chat Studio still shows a duplicate agent dropdown in the desktop window titlebar (by minimize). Only the left Show-in-Chat picker may remain.

## 2. What to Build
Stop Agent Desktop from injecting `.desktop-win-agent-select` into the Chat window titlebar. Keep `#agentSelect` in Chat top bar only.

## 3. Acceptance Criteria (Definition of Done)
- [x] `buildTitleExtras` does not inject a Chat titlebar agent dropdown
- [x] No re-inject timer/MutationObserver recreates it
- [x] Vitest asserts no `desktop-win-agent-select` injection path
- [x] Live serve: Chat window titlebar has no agent `<select>` next to minimize

## Design lock
- One agent picker only (left / Show in Chat). Remove titlebar duplicate.
