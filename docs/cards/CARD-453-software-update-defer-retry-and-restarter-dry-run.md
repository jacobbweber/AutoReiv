---
id: CARD-453
title: "Software-update auto scheduler defer-retry cadence + Windows restarter dry-run proof"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-451
labels:
  - type:chore
  - area:system
  - P3
---

# [CARD-453] Software-update auto scheduler defer-retry cadence + Windows restarter dry-run proof

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-451 build — busy deferral is proven with injectable BusyDetector; scheduler ticks every 60s but dedicated N-minute defer cadence + DetachedScriptRestarter Windows dry-run are not separately contracted
> **Related**: CARD-451

## Intent

1. Make daily auto-update deferral retry interval explicit (e.g. every N minutes while busy, bounded) rather than relying only on the 60s tick + per-day cap.
2. Add a hermetic dry-run proof that `DetachedScriptRestarter` builds the correct `restart_serve.ps1 -HostAddr … -Port …` command line without spawning a real restart (never against live Jarvis serve from tests).

## Acceptance (EARS)

- **[REQ-453-001]** WHEN auto-update is deferred for busy, THE SYSTEM SHALL record next-retry time and honor a configurable defer interval (default 15 minutes) up to a daily bound.
- **[REQ-453-002]** THE SYSTEM SHALL unit-test DetachedScriptRestarter command construction with a fake Popen (no real process) preserving host/port.

## Reply phrases

- Start: say **build**.
