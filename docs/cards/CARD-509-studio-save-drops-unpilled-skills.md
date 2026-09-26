---
id: CARD-509
title: "An Agent Studio save turns off every skill that has no pill (for example AutoReiv's coding skill)"
status: Ready
created: 2026-09-25
updated: 2026-09-25
branch: qa
related:
  - CARD-450
  - CARD-502
  - CARD-505
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-509] An Agent Studio save turns off every skill that has no pill (for example AutoReiv's coding skill)

> **Status**: Ready (found in the CARD-505 build repro, 2026-09-25 ET; existed before CARD-505)
> **Related**: CARD-450 (platform defaults), CARD-502 (shared save and operator skill lists), CARD-505
> **Labels**: `type:bug`, `area:agents`, `P2`

## What was seen

On a scratch install (never Jacob's AppData), one Max-Turns-only Save in Agent Studio on AutoReiv and one on Developer left settings key `platform_operator_disabled_skills` as `{"autoreiv":["coding"],"developer":["build-agent-pack"]}`. Neither skill was touched. Those skills are now off for the agent and stay off after restart.

Side effect: AutoReiv's skill list no longer matches the platform seed, so every restart reports AutoReiv as `promoted` (re-applied) instead of `unchanged`. It stays unlocked, so this is noise, not a lock.

Jacob's live install currently has `{"tutor": []}` in that key (read-only check), so it is not affected yet. It will be after his next Studio Save on AutoReiv or Developer.

## Suspected cause (to confirm)

`src/web/static/modules/studios/forge.js` L417 builds the saved skill list with `allowlistForSave(fromPills...)` from `skill_pills.js`. Only skills that have a pill in the Studio are sent. The server treats a missing platform skill as operator-disabled (CARD-502 disabled-skills bookkeeping).

## Direction

- Save should send the agent's full skill list: the pill state for pilled skills, and the unchanged current value for skills without a pill. Alternatively the server could only count a skill as disabled when the request explicitly lists it as off.
- Tests: Vitest for the payload (an unpilled skill stays in the list); unit test that a scalar-only PUT leaves `platform_operator_disabled_skills` unchanged; smoke desktop and phone: Max Turns save keeps `coding` on AutoReiv.
- Consider a one-time repair for installs that already recorded pill-less skills as disabled (only when the disable came from a save that did not show that skill).
