# [CARD-305] Remove Sessions from dock (Chat owns sessions)

> **Status**: Done
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13

## Intent
Sessions is not a desktop dock studio. Chat in-studio drawer owns New Conversation / recent chats.
Hard-gate: no dock launcher, no resurrected Sessions desktop window from prefs.

## Acceptance
- [x] DOCK_LAUNCHERS has no sessions
- [x] Prefs scrub sessions on load/persist
- [x] openWindow('sessions') opens Chat + sessions drawer
- [x] Vitest contract
