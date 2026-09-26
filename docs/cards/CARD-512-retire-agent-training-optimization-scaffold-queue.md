---
id: CARD-512
title: "Agent Studio's \"Agent Training Optimization\" queue is always empty; retire the scaffold spine"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-496
  - CARD-497
  - CARD-498
labels:
  - type:cleanup
  - area:agents
  - P3
---

# [CARD-512] Retire the always-empty "Agent Training Optimization" queue (scaffold spine)

> **Status**: Ready (found in the CARD-495 audit, 2026-09-25 ET). Not next: build after CARD-497 and before CARD-498.
> **Related**: CARD-495 audit F16 and decision D8, CARD-496 (removes the panel), CARD-498 (data drop)
> **Labels**: `type:cleanup`, `area:agents`, `P3`

## Problem

Agent Studio shows an "Agent Training Optimization" panel with a candidate queue and an "Open Training Factory" button (`templates/index.html` L1615-1642, `forge/scaffold.js` L159-210, L366-380). The queue reads `/api/capabilities/scaffold/*` (`routers/capabilities.py` L258 draft, L282 candidates), backed by `SelfScaffoldSpine` (`app.py` L533-555) and the `scaffold_spine` table (`schema.py` L474). The only thing that adds a candidate is `POST /api/capabilities/scaffold/draft`, and no UI or agent calls it (rg on qa `10f2bc75`). So the queue is always empty and overlaps Tools Studio.

## Four Beats

- **Want:** no dead training panels or routes.
- **Today:** an empty panel (removed by CARD-496) and a backend nobody feeds.
- **Change:** first confirm on a scratch server that nothing adds candidates (search logs and code again). Then delete the scaffold routes, `SelfScaffoldSpine` and its wiring; export `scaffold_spine` rows in CARD-498 before dropping the table.
- **Done when:** `/api/capabilities/scaffold/*` is gone (410 or 404 with a note), the rest of `/api/capabilities/*` still works, and tests pass.

## Acceptance (EARS)

- THE system SHALL NOT serve `/api/capabilities/scaffold/*` after this card.
- `/api/capabilities/registry` and other capabilities routes SHALL still return 200.

## Tests

- Delete tests that only cover the scaffold spine; keep capabilities registry tests.
- Integration: scaffold routes are gone; registry route 200.

## Runbook (scratch server)

1. Agent Studio has no "Agent Training Optimization" panel.
2. `GET /api/capabilities/registry` returns 200; `GET /api/capabilities/scaffold/candidates` does not.
