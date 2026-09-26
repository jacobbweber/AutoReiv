---
id: CARD-536
title: "Reopening a chat whose job failed shows Failed without the reason and names the last queued phase"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-530
  - CARD-485
labels:
  - type:bug
  - area:chat
  - P3
---

# [CARD-536] Reopened failed job strip has no reason

> **Status**: Ready (found while building CARD-530, 2026-09-26 ~5:32 PM ET). P3: cosmetic, the reason is in Observability.
> **Related**: CARD-530 (REQ-530-007 covers the live strip), CARD-485 (journey hydrate)
> **Labels**: `type:bug`, `area:chat`, `P3`

## Evidence

- After the CARD-530 startup repair, Jacob's `job_3bdef1802655` (session `d09a88dd-...`) is `failed`; the reason is in the phase output packet and the `reconciled_stuck_phase` journey event.
- `hydrateJobPhaseStateFromJourney` (`chat/session_select.js`) sets `jobStatus` failed / FAILED but no `failReason`, and picks the last phase (Execute, still `queued`) as the active phase. `/api/chat/sessions/{id}/journey` carries no fail reason.

## Change (decide at refinement)

Include the failed phase and its reason in the session journey; hydrate `failReason` and pick the failed phase for the strip.

## Done when

Reopening a chat whose job failed shows "Job failed: <reason>" and the phase that failed.
