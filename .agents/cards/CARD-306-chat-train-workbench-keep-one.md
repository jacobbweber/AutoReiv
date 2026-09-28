# [CARD-306] Chat Train keep-one + Workbench honesty

> **Status**: Done
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13

## Intent
Leftover #2 honesty:
1. Remove **Train in Lab** chrome (Forge gap button). Keep `/gaps/.../train` backend — Factory Train still uses it.
2. **Workbench** stays — live paths: message Open→pane, and session artifact APIs (`/api/sessions/{id}/artifacts`, `/api/artifacts/{id}`). Empty shelf shows honest empty state.
3. Hide Chat +Options **Train Agent** checkbox — Training Factory owns training/candidate surface (keep-one).

## Acceptance
- [x] No "Train in Lab" label in Forge UI
- [x] trainAgentToggle not visible in Chat Options
- [x] workbenchToggleBtn remains; empty state honest
- [x] Factory Train button + handshake modal retained
- [x] Vitest chrome contract
