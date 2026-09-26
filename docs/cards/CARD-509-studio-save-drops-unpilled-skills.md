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
  - CARD-508
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-509] An Agent Studio save turns off every skill that has no pill (for example AutoReiv's coding skill)

> **Status**: Ready (found in the CARD-505 build repro; refined 2026-09-25 10:30 PM ET on qa after the CARD-505 merge; existed before CARD-505)
> **Related**: CARD-450 (platform defaults), CARD-502 (shared save and operator skill lists), CARD-505
> **Labels**: `type:bug`, `area:agents`, `P2`

## What was seen

On a scratch install (never Jacob's AppData), one Max-Turns-only Save in Agent Studio on AutoReiv and one on Developer left settings key `platform_operator_disabled_skills` as `{"autoreiv":["coding"],"developer":["build-agent-pack"]}`. Neither skill was touched. Those skills are now off for the agent and stay off after restart.

Side effect: AutoReiv's skill list no longer matches the platform seed, so every restart reports AutoReiv as `promoted` (re-applied) instead of `unchanged`. It stays unlocked, so this is noise, not a lock.

Jacob's live install: see the next section (AutoReiv `coding` is on; Developer `build-agent-pack` is already off).

## Jacob's live install (read-only check, 2026-09-25 ~10:25 PM ET, after the CARD-505 merge)

- AutoReiv: `coding` is **on** (stored list equals the 13-skill platform seed, updated by the CARD-505 first start at 10:07 PM ET). `platform_operator_disabled_skills` is still `{"tutor": []}` (last written 2026-09-24 6:32 PM ET). No Studio save has hit AutoReiv since the CARD-502 bookkeeping.
- Developer: `build-agent-pack` is **off** (stored list: proposals, sdlc-engineering, mcp-engineering, native-tool-engineering, capability-authoring). It is not in the disabled map, so the startup merge does not know it was dropped, and Developer is locked (real prompt edit), so the seed does not put it back.
  - Backups show it was on at 2026-09-24 1:47 PM ET and off by 6:32 PM ET. The Reset to platform defaults at 7:01:05 PM ET should have restored it, but Developer's row was saved again at 7:01:36 PM ET (the SOLID/DRY prompt edit) and it is off again. That timing fits this bug (a Studio Save 30 s after Reset, before CARD-502 recorded disables), but it is not proven.
  - The seed gave Developer `build-agent-pack` on 2026-09-23 (CARD-429, `3b121436`).

## Root cause (qa `53f798d6`)

1. Pills come from three lists only: the skills catalog `platform_skills` / `operator_skills` (`GET /api/skills/catalog`, `forge/runbook.js` `loadPlatformSkills` L216) and the agent's `pack_skills` (`renderAssignedSkills` L157-177).
2. `pack_skills` is built from the pack manifest's `skills` array, minus platform skill ids (`src/web/routers/agents.py` `_pack_skills_payload` L75-104). AutoReiv's `platform-packs/autoreiv/pack.json` `skills` array has no `coding` entry (it is only in `allowed_skill`; the folder is `platform-packs/autoreiv/skills/coding`). Developer's manifest has no `build-agent-pack` entry (that folder lives in the AutoReiv pack). Live check: neither id is in the catalog or in the agent's `pack_skills`, so neither gets a pill.
3. Save builds the list from pressed pills only: `src/web/static/modules/studios/forge.js` L413-417 (`pillNodes` -> `pressedSkillIds` -> `allowlistForSave`, `forge/skill_pills.js` L61). A skill with no pill is left out.
4. The server records every stock skill missing from the saved list as operator-disabled: `src/application/agent_packs/skill_list.py` `persist_agent_profile` L94 -> `record_operator_disabled_skills` (`platform_pack_promotion.py` L191). The startup merge then keeps it off (`platform_pack_promotion.py` L872 `get_operator_disabled_skills`).

## Decisions (recommendations; Jacob to confirm)

- D1. Fix in the client: Save sends pill state for pilled skills and keeps every skill without a pill exactly as loaded (`lastAllowedSkills`, `forge.js` L157/L327). One helper in `skill_pills.js` (for example `mergePillsWithUnpilled(loaded, pillIds, pressedIds)`), Vitest-covered.
- D2. Also guard the server: `persist_agent_profile` records a skill as disabled only if the request could have shown it (it is in the agent's manifest skills, the catalog, or operator-added). Keeps other clients (API, older tabs) from causing the same loss.
- D3. Show the missing skills: add the manifest-less allowed skills (`coding` on AutoReiv, `build-agent-pack` on Developer) as pills, so they can be switched on and off in Studio. Alternative: add the `coding` entry to AutoReiv's manifest `skills` array. Recommend showing a pill for every id in `allowed_skill` or the seed that has a `SKILL.md`.
- D4. Repair Jacob's Developer: do not auto-repair a locked agent's skill list at startup. Tell Jacob to switch `build-agent-pack` back on in Studio once D3 ships (or run Reset and re-apply the SOLID/DRY line). Recommend the manual step, because Developer is locked on purpose.
- D5. One-time repair for disabled-map entries written by this bug: none needed on live (`{"tutor": []}`). Skip it.

## Tests first (red, then fix)

- Vitest: a save with pills for A and B (B off) and loaded list [A, B, coding] sends [A, coding].
- Unit: a Max-Turns-only `PUT /api/agents/autoreiv` with the full list leaves `platform_operator_disabled_skills` unchanged. A PUT that leaves out a skill the Studio could not show does not record it as disabled (D2).
- Unit: the agent payload (or the catalog) exposes a pill for `coding` on AutoReiv and `build-agent-pack` on Developer (D3).
- Smoke desktop and phone: open AutoReiv, change Max Turns, Save, reload, and `coding` is still on. Restart, and AutoReiv reports `unchanged` (not `promoted`).

## Out of scope

- CARD-508 (Studio form snaps back to the previous agent on a fresh page).
