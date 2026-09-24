---
id: CARD-450
title: "Studio UI for platform pack promotion skips and Reset to platform defaults"
status: In Review
branch: feat/card-450-studio-platform-pack-reset
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

# [CARD-450] Studio UI for platform pack promotion skips and Reset to platform defaults

> **Status**: In Review
> **Branch**: `feat/card-450-studio-platform-pack-reset`
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

1. Agent Studio shows a **Platform defaults** section on every platform agent (`is_platform_pack=true`). It holds one status badge, one **Reset to platform defaults** button, and a per-agent **Backups** list.
2. The badge appears only when this agent's entry in the last sync report is `skipped_user_modified` or `promoted_partial`. Copy is plain English, e.g. "Platform update skipped because the system prompt was edited" or "Platform update partly applied. Kept your edited: system prompt". `skipped_fields` are shown in plain words, never raw field names. The badge points at Reset. `unchanged`, `promoted`, `force_reset`, or no entry show no badge.
3. **One button only.** There is no separate "Accept platform version" control; Reset calls `POST /api/agents/{id}/accept-platform-seed` after a confirm dialog.
4. The Reset confirm dialog lists what is replaced and what is kept. Both lists are derived from `promote_one_platform_pack` / `backup_pack_content`, not guessed, and the dialog says a backup is saved first:
   - **Replaced:** system prompt (instructions); skill files that ship with the agent (stock `skills/*/SKILL.md` refreshed, retired stock skills removed); which skills are on (the platform list; skills you turned off come back on); the platform tool list (pack tools plus tools from platform skills).
   - **Kept:** max turns and model (`_preserve_operator_scalars`), plus every setting promotion never touches (name, description, provider and API settings, tone, memory, storage, Show in Chat, credentials, MCP servers). Skill folders you created yourself stay on disk.
5. After Reset, Studio re-reads `GET /api/agents/{id}`, `GET /api/platform-packs/sync-status` and the backups list, so the badge clears.
6. **Backups list:** reads `GET /api/agents/{id}/pack-content-backups`. It shows each backup's local readable time (ISO tooltip) and a plain reason ("Before reset to platform defaults", "Before automatic reset"). A **Restore** button opens its own confirm dialog, then calls the CARD-449 restore endpoint. Restore brings back instructions, skill list, tool list, max turns and model from the snapshot, and marks the agent customized. Skill files on disk are not changed.
7. Thinnest backend changes found necessary while building (no new promotion rules):
   - **Reset really resets.** Today accept-platform-seed clears the lock but the clean path still keeps an edited prompt (`promoted_partial`) and operator-disabled skills. Reset now runs the same pack through the existing CARD-449 force-reset path (`force_reset=True` for that one pack) and clears that pack's disabled-skill record, so the result matches the dialog.
   - **Single-pack runs merge the report.** Today a `pack_ids=[id]` promotion overwrites the whole `platform_pack_sync_last_report` with one entry, so every other agent's status disappears. Single-pack runs now replace only their own entries.
   - **Restore refreshes the report.** Today, restoring a backup locks the agent but the report still says it was reset, so the badge would not return. Restore now re-runs promotion for that one pack (it reports `skipped_user_modified` for a locked agent) so the badge comes back.

### Beat 4: What dies today

1. Operators finding a stuck pack only by reading serve logs or manually calling `/api/platform-packs/sync-status`.
2. Not knowing what Reset does. The confirm dialog becomes the operator contract for replaced vs kept.
3. No Studio path to reset one agent to platform defaults while keeping max turns and model, or to undo that reset.
4. The separate "Accept platform version" concept (merged into Reset).
5. A single-pack sync wiping other agents' status from the last report.

---

## 2. Acceptance criteria (EARS)

- **[REQ-450-001]** WHEN the last platform-pack sync report includes a pack with `status=skipped_user_modified`, THE SYSTEM SHALL show a badge on that agent's Platform defaults section in Agent Studio. The badge copy names the edited condition in plain words and points at **Reset to platform defaults**.
- **[REQ-450-002]** WHEN the last report includes `status=promoted_partial` with `skipped_fields`, THE SYSTEM SHALL list the kept fields in plain words (e.g. "system prompt") in that same badge. Raw field names are never shown.
- **[REQ-450-003]** WHEN the operator confirms **Reset to platform defaults** for a platform agent, THE SYSTEM SHALL call `POST /api/agents/{id}/accept-platform-seed` and then refresh Studio from `GET /api/agents/{id}` and `GET /api/platform-packs/sync-status`, so the badge clears without a manual HTTP client. There is no separate Accept control.
- **[REQ-450-004]** THE Reset confirm dialog SHALL list Replaced (system prompt, shipped skill files, skill on/off list, platform tool list) vs Kept (max turns, model, and all other settings such as provider), and SHALL state that a backup is saved first.
- **[REQ-450-005]** WHEN Reset runs, THE SYSTEM SHALL write a CARD-449 backup first and apply the platform version through the existing force-reset promotion path, so an edited system prompt and turned-off skills are replaced while max turns and model are kept.
- **[REQ-450-006]** Live proof SHALL use a currently content-locked platform pack on Jarvis (**developer**) for badge data, and SHALL prove Reset and Restore end-to-end on a fixture app in tests. Developer stays locked so Jacob can run Reset live from the UI.
- **[REQ-450-007]** WHEN a pack's last status is `unchanged`, `promoted` or `force_reset` (or it has no entry), THE SYSTEM SHALL NOT show a badge.
- **[REQ-450-008]** THE Platform defaults section SHALL list that agent's pack-content backups from `GET /api/agents/{id}/pack-content-backups`, newest first. Each entry shows local readable time with an ISO tooltip and a plain-English reason, or an empty-state line when there are none.
- **[REQ-450-009]** WHEN the operator confirms **Restore** on a backup in its own confirm dialog, THE SYSTEM SHALL call `POST /api/agents/{id}/pack-content-backups/{backup_id}/restore`, refresh the pack's sync-status entry, and re-render the agent. A restored customized agent shows the skip badge again.
- **[REQ-450-010]** WHEN a promotion runs for a subset of packs (`pack_ids`), THE SYSTEM SHALL replace only those packs' entries in the last sync report and keep every other pack's entry.

---

## 3. Proof / live-test notes

0. Build decisions (Jacob, 2026-09-24): one Reset button, no separate Accept; badge only for skipped/partial; dialog Replaced vs Kept derived from code; backups list with Restore is in scope; AppData is disposable during development (tests use fixture apps, never live AppData).
1. Confirm `POST http://127.0.0.1:8000/api/platform-packs/sync` still reports content-locked packs as `skipped_user_modified` (or recreate the lock on a fixture pack). Scalar-only agents should promote under CARD-449.
2. Open Agent Studio for that pack: badge/status visible without opening DevTools or logs; **Reset to platform defaults** visible for platform agents.
3. Open Accept/Reset confirm: replace vs preserve list matches CARD-443/449; note backup will be written.
4. Accept/Reset -> status clears or becomes `promoted` / `unchanged`; `GET /api/agents/{id}` reflects platform pack-owned fields; `max_turns`/`model` unchanged if they were operator-set; `GET /api/agents/{id}/pack-content-backups` shows the snapshot.
5. Negative: a pack with `status=unchanged` does not show a false "update available" badge.

---

## 4. Constraints

- Jacob said **build** on 2026-09-24.
- Do not reimplement promotion logic; consume CARD-443/449 APIs.
- Do not silently call accept-platform-seed without confirm.
- Do not merge to `main`; no version bump for this scaffold.
- Prefer one Agent Studio surface; avoid a second parallel notification system unless Four Beats agree.

---

## 5. Reply phrases

- Refine the UI contract: say **continue**.
- Start implementation: say **build**.
- After Studio live proof: say **merge to qa**.

---

## 6. Build notes and proof (2026-09-24, Jarvis)

**Branch:** `feat/card-450-studio-platform-pack-reset` (from `qa` `e54021ff`; not pushed or merged).

**Where:** Agent Studio -> pick a platform agent (AutoReiv, Direct, Developer, Tutor) -> the **Platform defaults** section at the top of the page.

**Changed:**
- `src/web/static/modules/studios/forge/platform_defaults.js` (new): badge, dialogs, backups list, reset/restore plus refresh.
- `src/web/static/modules/studios/forge.js`: wiring.
- `src/web/templates/index.html`: section and two dialogs using the shared modal manager.
- `src/infrastructure/skills/platform_pack_promotion.py`:
  - `force_reset` parameter.
  - `reset_platform_pack_to_defaults`.
  - Subset report merge.
  - Restore writes the operator override.
- `src/web/routers/agents.py`:
  - Reset delegates to the helper.
  - Restore re-runs a report-only promotion for that pack (`force_reset=False`).

**Bugs found and fixed while building:**
1. Accept/Reset kept an edited system prompt (`promoted_partial`) and turned-off skills. It now uses the force-reset path (REQ-450-005).
2. Single-pack runs wiped every other pack from the last report (REQ-450-010).
3. Restore saved only the base profile, and the operator override hid it, so restore looked like a no-op in `GET /api/agents/{id}`.
4. With keep-customizations off, the post-restore refresh force-reset the restored content straight away.

**Tests:**
- `tests/unit/agent_packs/test_card_450_platform_reset.py`: 6 tests, including reset and restore end to end on an isolated `create_app()`.
- `tests/unit/frontend/card_450_platform_defaults.test.js`: 14 tests.
- CARD-443/449/450 backend: 20 passed.
- Broad `tests/unit`: 1972 passed, 11 skipped, 2 failed. Both failures are known: CAP-001 linter (CARD-454) and the CARD-388 AppData-name flake (CARD-455).
- Vitest: 747 passed, 5 failed, all pre-existing on `qa` (CARD-456).
- Playwright smoke: 7/7. Honesty smoke: green.
- Ruff and ESLint are clean on our files. Full-repo ruff went from 12 to 10 errors (CARD-454). Full-repo ESLint errors are pre-existing (CARD-456).

**Live (serve restarted on 0.0.0.0:8000, tip `8ea1b429`; DB backed up to `AutoReiv\backups\autoreiv-pre-card450-20260924-181534.db`):**
- `developer` = `unchanged` ("seed_content_hash already matches platform seed"), badge none.
- `tutor` = `unchanged`, badge none.
- Developer was **not** content-locked. Keep-customizations is **off** live, and a boot at 13:47 ET force-reset Developer (backup `developer-20260924T174716805725`, reason `force_reset_keep_customizations_off`).
- Reset was not run live. Jacob runs it from the UI.

**Follow-ups:** CARD-456 (frontend Vitest/ESLint debt), CARD-457 (badge after Save and keep-customizations-off notice), CARD-458 (lock-migration report merge; restore turned-off-skills record).
