---
id: CARD-508
title: "Agent Studio Platform defaults badge seen empty after quickly switching agents (unconfirmed)"
status: Ready
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-450
  - CARD-505
labels:
  - type:bug
  - area:agents
  - P3
---

# [CARD-508] Agent Studio Platform defaults badge seen empty after quickly switching agents (unconfirmed)

> **Status**: Ready (investigate first; found while refining CARD-505, 2026-09-25 9:35 PM ET)
> **Related**: CARD-450 (Platform defaults section), CARD-505
> **Labels**: `type:bug`, `area:agents`, `P3`

## What was seen

On the CARD-505 scratch server (AutoReiv and Developer both `skipped_user_modified` in `/api/platform-packs/sync-status`, with identical entries), a Playwright script opened Agent Studio once and switched agents with `selectOption` every 1.5 s:
- Order autoreiv, tutor, developer, direct: AutoReiv's `#forgePlatformUpdateText` was empty ("This agent has the latest platform update" showed) and Developer's badge was right.
- Order tutor, autoreiv, direct, developer: the same result.
- A fresh page per agent, waiting 3 s, showed the correct badge for both ("You edited the system prompt...").

Script: `scratch/c505_badge.cjs` (fast switching) vs `scratch/c505_badge2.cjs` (fresh page).

## Suspected cause (to confirm)

`setupPlatformDefaults().render(agent)` in `src/web/static/modules/studios/forge/platform_defaults.js` (L243-260 `paint`, `loadPlatformDefaultsData` L180-198) does three fetches per agent and does not guard against an older agent's answer arriving after a newer one. An out-of-order paint, or a render skipped for the initially selected agent, would leave the wrong badge.

## Direction

- Reproduce by hand: open Agent Studio, switch between two locked agents and an unlocked one quickly, and watch the badge.
- If confirmed: tag each load with the agent id and drop answers for an agent that is no longer selected. Add Vitest for out-of-order answers and a smoke check (desktop and phone).
- If not reproducible by hand: close as test-script timing.
