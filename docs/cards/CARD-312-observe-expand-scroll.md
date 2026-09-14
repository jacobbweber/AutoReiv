# [CARD-312] Observe expand scroll (phone + desktop)

> **Status**: Done
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-14

## Intent
Expanded Observe sections must be fully reachable. Studio panel/page scrolls; expand must not clip content with a non-scrolling trap.

## Acceptance
- [x] `#view-observability` scrolls (`min-h-0` + `overflow-y: auto`)
- [x] Desktop hosted Observe window scrolls inside bounds
- [x] Open `details.obs-section` overflow visible; body max-height none
- [x] Cache bump `app.js?v=2.0.48`
