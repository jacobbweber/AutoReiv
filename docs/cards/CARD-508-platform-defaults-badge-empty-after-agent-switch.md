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

## New evidence (CARD-505 build, 2026-09-25 ET)

On a fresh Agent Studio page (AutoReiv selected first), `selectOption` to Developer made the whole form snap back to AutoReiv, not only the badge: the name field showed AutoReiv, and the network log fetched `/api/agents/autoreiv/pack-content-backups` after the Developer requests. That points at a late Studio load re-rendering the previously selected agent over the newer choice (the Studio's initial agent load, not just `platform_defaults.js`). Debug script: `scratch/c505_badge_dbg.cjs`.

With the CARD-505 fix, AutoReiv's badge on a fresh page is correctly hidden (it is up to date), so the original "empty badge" sighting for AutoReiv is expected now. The open question is the snap-back.

Direction update: first reproduce by hand (open Agent Studio, immediately pick Developer, wait 3 s, check the name field). If confirmed, guard both the Studio agent load and the Platform defaults load with the selected agent id.

## New evidence (CARD-509 build, 2026-09-25 ~10:45 PM ET)

On a fresh scratch install, a script opened Agent Studio, waited until the agent options existed plus 2.5 s, then picked Developer. The picker itself went back to AutoReiv (`#forgeAgentSelect` value `autoreiv`, name field "AutoReiv"). A Save then sent `PUT /api/agents/autoreiv`, so it saved the agent shown on screen, not the one picked. No wrong-agent write was seen. Picking again after 2.5 s stuck. Smoke TC-38 picks with a retry loop for this reason.
