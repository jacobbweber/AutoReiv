---
id: CARD-450
title: "Studio UI for platform pack promotion skips and accept-platform-seed"
status: Ready
created: 2026-09-24
adr: ADR-0056
labels:
  - type:ux
  - area:packs
  - area:studio
  - P2
parent: CARD-443
related:
  - CARD-449
---

# [CARD-450] Studio UI for platform pack promotion skips and accept-platform-seed

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-443 live proof on Jarvis (`feat/card-443-platform-pack-appdata-sync`)
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)
> **Labels**: `type:ux`, `area:packs`, `area:studio`, `P2`
> **Parent**: [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md)
> **Related**: [CARD-449](./CARD-449-scalar-operator-edits-max-turns-must-not-lock-platform-pack-promotion.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine badge copy, confirm-dialog fields, or which Studio surface hosts the control - **still no product code** |
| **`build`** | Implement Agent Studio (or agreed operator surface) visibility for promotion skips + Accept / Reset to platform defaults |
| **`merge to qa`** | After live proof that a skipped pack shows in Studio and Accept/Reset applies the documented replace-vs-preserve contract |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md) APIs: `GET /api/platform-packs/sync-status`, `POST /api/platform-packs/sync`, `POST /api/agents/{id}/accept-platform-seed` |
| **Depends on** | [CARD-449](./CARD-449-scalar-operator-edits-max-turns-must-not-lock-platform-pack-promotion.md) backup + finer locks (`GET /api/agents/{id}/pack-content-backups`, keep-customizations setting) |
| **Blocked by** | Nothing for scaffolding; UI build should land after CARD-449 is In Review / on `qa` |
| **Unlocks** | Operators can resolve `user_modified` / partial prompt skips and reset to platform defaults without reading serve logs or calling raw HTTP |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. When platform-pack promotion skips or only partially applies, the operator must see that in the product UI - not only in a log WARNING or by curling the API.
2. Accepting the platform version must be an explicit Studio action with a confirm dialog that lists what will be replaced versus what stays (e.g. `max_turns`, `model`, operator-edited `system_prompt` when baseline skipped).
3. Each platform agent in Agent Studio needs a **"Reset to platform defaults"** button that calls `accept-platform-seed` / reset endpoint, shows a confirm dialog listing replaced vs kept, and uses the CARD-449 backup so prior content can be restored.
4. Live Jarvis state after CARD-443: **developer** may remain content-locked; Tutor scalar-only lock should clear under CARD-449. Skips must still be visible in Agent Studio.

### Beat 2: What AutoReiv does now

1. CARD-443 promotion results (`skipped_user_modified`, `promoted`, `promoted_partial` with `skipped_fields`, `unchanged`) are written to setting `platform_pack_sync_last_report` and returned by:
   - `GET http://127.0.0.1:8000/api/platform-packs/sync-status`
   - `POST http://127.0.0.1:8000/api/platform-packs/sync`
2. Resolution API: `POST http://127.0.0.1:8000/api/agents/{agent_id}/accept-platform-seed` clears `user_modified` and re-promotes that pack. CARD-449 adds backup-before-reset + listing endpoint.
3. Skip path also logs a WARNING with the resolution string. There is **no** Agent Studio badge, toast, inbox item, Confirm dialog, or per-agent Reset button wired to these endpoints.
4. Source of truth for stock content remains `platform-packs/<pack>/`; live copy is AppData `packs/<pack>/`; profile brain is SQLite under user data.

### Beat 3: What will change

1. Agent Studio (or one agreed operator surface) shows a durable badge/status for platform packs when the last sync report says `skipped_user_modified` or `promoted_partial` (e.g. "Platform update available - skipped because edited" / "Platform update partially applied - system_prompt kept").
2. An **Accept platform version** control calls `POST /api/agents/{id}/accept-platform-seed` (or a thin Studio wrapper) only after a confirm dialog lists:
   - **Replaced**: stock `pack.json` projection fields owned by the platform seed, stock `skills/*/SKILL.md`, pack-owned profile fields (`allowed_skill`, pack tools, and `system_prompt` when accepting full seed).
   - **Preserved**: operator scalars such as `max_turns` and `model` (CARD-443/449 contract); any fields the dialog documents as kept.
3. A per-agent **"Reset to platform defaults"** button in Agent Studio uses the same accept-platform-seed / reset endpoint, with a confirm dialog listing replaced vs kept, and relies on CARD-449 backup so the previous prompt/skills/tools/settings snapshot is available for restore.
4. After Accept/Reset, Studio refreshes agent detail from `GET /api/agents/{id}` and sync status from `GET /api/platform-packs/sync-status` so the badge clears or updates.
5. Docs-only until **build**; no new promotion rules in this card (CARD-449 owns scalar-vs-pack lock policy + backups).

### Beat 4: What dies today

1. Operators discovering a stuck pack only by reading serve logs or manually calling `/api/platform-packs/sync-status`.
2. Ambiguity about what Accept/Reset does - the confirm dialog becomes the operator contract for replace vs preserve.
3. No Studio path to reset one agent to platform defaults while keeping max_turns/model.

---

## 2. Acceptance criteria (EARS)

- **[REQ-450-001]** WHEN the last platform-pack sync report includes a pack with `status=skipped_user_modified`, THE SYSTEM SHALL surface that pack in Agent Studio (or the agreed operator surface) with copy that names the user-modified / edited condition and points at Accept platform version.
- **[REQ-450-002]** WHEN the last report includes `status=promoted_partial` with `skipped_fields` (e.g. `system_prompt`), THE SYSTEM SHALL surface the skipped field names in that same operator-visible status.
- **[REQ-450-003]** WHEN the operator confirms Accept platform version for a platform pack id, THE SYSTEM SHALL call the existing accept path (`POST /api/agents/{id}/accept-platform-seed` or equivalent) and refresh Studio from `GET /api/agents/{id}` + `GET /api/platform-packs/sync-status` without requiring a manual HTTP client.
- **[REQ-450-004]** THE confirm dialog SHALL list what gets replaced vs preserved using the CARD-443/449 contract (at least: stock skills / pack-owned allowlists replaced; `max_turns` and `model` preserved).
- **[REQ-450-005]** WHEN the operator uses per-agent **Reset to platform defaults** in Agent Studio, THE SYSTEM SHALL call accept-platform-seed / reset after a confirm dialog listing replaced vs kept, and SHALL rely on the CARD-449 backup written before the reset.
- **[REQ-450-006]** Live proof SHALL use a currently skipped or content-locked platform pack on Jarvis (e.g. **developer**) or an equivalent fixture, and record before/after Studio visibility plus sync-status.
- **[REQ-450-007]** WHEN a pack has `status=unchanged` and is not content-locked, THE SYSTEM SHALL NOT show a false "update available" badge.

---

## 3. Proof / live-test notes

1. Confirm `POST http://127.0.0.1:8000/api/platform-packs/sync` still reports content-locked packs as `skipped_user_modified` (or recreate the lock on a fixture pack). Scalar-only agents should promote under CARD-449.
2. Open Agent Studio for that pack: badge/status visible without opening DevTools or logs; **Reset to platform defaults** visible for platform agents.
3. Open Accept/Reset confirm: replace vs preserve list matches CARD-443/449; note backup will be written.
4. Accept/Reset -> status clears or becomes `promoted` / `unchanged`; `GET /api/agents/{id}` reflects platform pack-owned fields; `max_turns`/`model` unchanged if they were operator-set; `GET /api/agents/{id}/pack-content-backups` shows the snapshot.
5. Negative: a pack with `status=unchanged` does not show a false "update available" badge.

---

## 4. Constraints

- This card is **docs-only** until Jacob says **build**. Status remains **Ready**.
- Do not reimplement promotion logic; consume CARD-443/449 APIs.
- Do not silently call accept-platform-seed without confirm.
- Do not merge to `main`; no version bump for this scaffold.
- Prefer one Agent Studio surface; avoid a second parallel notification system unless Four Beats agree.

---

## 5. Reply phrases

- Refine the UI contract: say **continue**.
- Start implementation: say **build**.
- After Studio live proof: say **merge to qa**.
