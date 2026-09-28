# [CARD-308] Wiki Graduate Inbox real pass/fail

> **Status**: Done
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13

## Intent
Graduate Inbox must not be a blind fast-move. Each inbox note is checked; failures stay in `00_Inbox` with inspectable reasons; passes graduate/merge to `01_Notes`.

## Rules (binary)
1. Non-empty body after fluff scrub
2. Real title (not empty / not `untitled`)
3. Non-empty domain
4. Non-empty topic

## Acceptance
- [x] Fail note remains in inbox with `graduate_errors` + action reason
- [x] Pass note moves/merges to warehouse
- [x] UI toast reports graduated vs held
- [x] Curate label stays gone; Graduate Inbox kept
