---
id: CARD-449
title: "Scalar operator edits (max_turns) must not lock platform pack promotion"
status: Ready
created: 2026-09-24
branch: feat/card-449-pack-lock-granularity
adr: ADR-0056
labels:
  - type:bug
  - area:packs
  - P1
parent: CARD-443
related:
  - CARD-445
  - CARD-450
---

# [CARD-449] Scalar operator edits (max_turns) must not lock platform pack promotion

> **Status**: Ready
> **Created**: 2026-09-24
> **Branch**: `feat/card-449-pack-lock-granularity`
> **Observed during**: CARD-443 live proof on Jarvis
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)
> **Labels**: `type:bug`, `area:packs`, `P1`
> **Parent**: [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md)
> **Related**: [CARD-450](./CARD-450-studio-ui-platform-pack-promotion-skips.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the scalar-vs-pack lock policy - still no product code |
| **`build`** | Implement finer-grained locks so max_turns/model edits do not block platform pack promotion |
| **`merge to qa`** | After proof that Tutor max_turns=100 survives while platform prompt/skills still promote |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Changing Tutor `max_turns` to 100 (CARD-445 intent) must not permanently block platform-pack to AppData / SQLite seed promotion.
2. Settings (max_turns, model, provider/choices) are operator preference and must never set the pack content lock and never be overwritten by promotion or reset.
3. Real pack-content edits (system_prompt vs shipped baseline, skill enable/disable, tool list changes the operator made) keep the full lock + CARD-443 skip/resolution.
4. AutoReiv's own automated additions must stop falsely locking agents as user_modified.
5. Operators need a global "Keep my agent customizations when platform packs update" toggle (default ON). When OFF, promotion force-resets pack-owned content but still preserves max_turns/model, after writing a restoreable backup.
6. Forced resets (global OFF or accept-platform-seed) must backup previous prompt/skills/tools/settings so they can be restored.

### Beat 2: What AutoReiv does now

1. `PUT /api/agents/{id}`, `POST /api/settings/agents/{id}`, `settings_service.save_agent_customization`, MCP attach/detach, `native_packaging` tool grants (~L351), `apply_user_modified_additive_skill_grants` (~L218/223), `apply_user_modified_developer_authoring_prompt` (~L319-330), and Factory `auto_pin` all call `mark_agent_user_modified(True)` indiscriminately - including scalar-only saves.
2. CARD-443 promotion skips the entire pack when `user_modified=true`, including stock `system_prompt` and skill allowlist updates.
3. Prompt baseline exists (`platform_shipped_prompt_hashes` / CARD-443) but the lock flag is not compared against it on save.
4. Live Tutor on Jarvis had `user_modified=1` with `max_turns=100` and a stale short SQLite prompt until `POST /api/agents/tutor/accept-platform-seed` cleared the lock.
5. Settings Studio Preferences already hosts **System & Software Updates** (`#settingsSystemUpdatesCard`, CARD-196). No separate app-update screen outside Settings.

### Beat 3: What will change

1. **Split settings vs content.** Settings fields (`max_turns`, `model`, provider/choices) never set the pack content lock (`user_modified`) and are never overwritten by promotion or reset.
2. **Prompt lock** counts as edited only when stored prompt hash != last shipped baseline (`platform_shipped_prompt_hashes`); compare actual content, not the flag alone.
3. **Skills/tools per item:** operator-disabled skills stay disabled after update (record operator-disabled set or compute vs last applied seed); new platform skills get added; tool lists for skills the operator did not change update from seed.
4. **Audit every `mark_agent_user_modified(True)` caller** in `agents.py`, `settings.py`, `settings_service.py`, `agent_training_factory.py`, `native_packaging.py`, `platform_packs.py`: only set the content lock when pack-owned content actually changed (prompt/skills/tools), not for scalar-only saves. Automated additive grants/prompt appends must stop setting the lock.
5. **Full lock + CARD-443 skip/resolution** remains only for real content edits.
6. **One-time startup migration:** re-evaluate currently locked platform agents (Tutor, Developer live); if only settings differ from seed/baseline, clear the lock and log/report; if real content divergence, keep locked. Report results under `GET /api/platform-packs/sync-status` (e.g. `lock_migration` section).
7. **Global setting** `platform_pack_keep_customizations` (default `true`). When `false`, promotion force-resets pack-owned content (prompt, skills, tools) to platform defaults for platform agents on sync/startup, still preserving `max_turns` and `model`. Expose in Settings UI Preferences (toggle + helper text warning that turning off resets edits on next update) **and** on the existing System & Software Updates card (same setting key).
8. **Backup before any forced reset** (global off or accept-platform-seed): persist previous `system_prompt`, skills, tools, settings for that agent (settings JSON keyed by agent + timestamp). Expose at minimum `GET /api/agents/{id}/pack-content-backups` listing backups; document restore path (implement a restore endpoint if small; else follow-up card).
9. **Tests (TDD, temp fixtures):** settings-only change still promotes; edited prompt skipped; disabled skill stays off while new skill added; automated additions do not lock; migration unlocks settings-only agents and keeps content-edited ones locked; global off forces reset but keeps max_turns/model and writes backup; default is on.

### Beat 4: What dies today

1. The need to manually clear `user_modified` after a harmless max_turns bump before platform Tutor skills/prompts can promote.
2. Automated platform grants/prompt appends falsely locking Developer/Tutor as permanently customized.
3. Ambiguity that any Studio save equals a pack-content lock.

---

## 2. Acceptance criteria (EARS)

- **[REQ-449-001]** WHEN only scalar operator fields (at least `max_turns` and `model`, plus provider/choices) differ from the platform seed, THE SYSTEM SHALL NOT set `user_modified` / the pack content lock and SHALL still promote pack-owned fields (`system_prompt` under shipped baseline, skills, pack tools) without requiring `accept-platform-seed`.
- **[REQ-449-002]** WHEN the operator has diverged pack content (stored `system_prompt` hash != shipped baseline, and/or operator-changed skills/tools) from the last applied seed, THE SYSTEM SHALL continue to refuse overwrite and surface the CARD-443 skip + resolution path.
- **[REQ-449-003]** WHEN comparing whether `system_prompt` is operator-edited, THE SYSTEM SHALL compare the stored prompt content hash to `platform_shipped_prompt_hashes` (actual content), not rely solely on the `user_modified` flag.
- **[REQ-449-004]** WHEN an operator has disabled a stock skill, THE SYSTEM SHALL keep that skill disabled after platform promotion WHILE still adding new platform skills the operator did not disable, and SHALL update tool lists for skills the operator did not change.
- **[REQ-449-005]** WHEN AutoReiv applies automated additive skill grants, developer authoring prompt appends, native packaging tool grants, or Factory auto_pin without an operator pack-content edit, THE SYSTEM SHALL NOT set `user_modified` / the pack content lock.
- **[REQ-449-006]** WHEN startup/sync runs a one-time lock migration, THE SYSTEM SHALL clear the content lock for platform agents whose only divergence is settings (max_turns/model/provider) and SHALL keep the lock when real content divergence exists, reporting results under `GET /api/platform-packs/sync-status`.
- **[REQ-449-007]** THE SYSTEM SHALL expose setting key `platform_pack_keep_customizations` defaulting to `true`. WHERE the setting is `false`, WHEN platform packs sync/promote, THE SYSTEM SHALL force-reset pack-owned content (prompt, skills, tools) to platform defaults for platform agents WHILE preserving `max_turns` and `model`, AFTER writing a per-agent backup.
- **[REQ-449-008]** WHEN a forced reset occurs (global keep-customizations off, or `accept-platform-seed`), THE SYSTEM SHALL persist a backup of previous system_prompt, skills, tools, and settings for that agent and SHALL expose at least `GET /api/agents/{id}/pack-content-backups` listing those backups (restore endpoint included when small).
- **[REQ-449-009]** THE Settings Studio Preferences section (including the existing System & Software Updates card) SHALL expose a clear toggle for "Keep my agent customizations when platform packs update" with helper text warning that turning it off resets pack-content edits on the next update. (Update screen exists inside Settings - toggle lives there as well as Preferences; no separate outside-Settings update app.)
- **[REQ-449-010]** Tutor live proof: `max_turns=100` remains after a settings-only PUT / platform pack update without clearing a full user_modified lock by hand; CARD-444 clause present; all 7 Tutor skills remain. Do NOT flip the global setting off on live data.

---

## 3. Implementation map

| Area | Path / notes |
|------|----------------|
| Promotion + migration + keep-customizations | `src/infrastructure/skills/platform_pack_promotion.py` |
| Automated grant lock audit | `src/infrastructure/skills/platform_packs.py`, `src/application/tools/native_packaging.py` |
| Save-path lock gating | `src/web/routers/agents.py`, `src/web/routers/settings.py`, `src/application/settings/settings_service.py`, `src/web/routers/agent_training_factory.py` |
| Setting key | `platform_pack_keep_customizations` via store `get_setting`/`set_setting` |
| Backup store | settings JSON e.g. `platform_pack_content_backups` (agent_id -> list of snapshots) |
| Settings UI | `src/web/templates/index.html` Preferences + `#settingsSystemUpdatesCard`; `src/web/static/modules/studios/settings.js` |
| Tests | `tests/unit/agent_packs/test_card_449_pack_lock_granularity.py` |
| Live data | `C:\Users\jacob\AppData\Local\AutoReiv\` (never checkout); backup `storage.db` before live proof |

---

## 4. Human verification runbook

1. Confirm serve on `0.0.0.0:8000` after `scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`.
2. `GET /api/platform-packs/sync-status` - inspect `lock_migration` for tutor/developer.
3. `PUT /api/agents/tutor` with `max_turns=100` (settings-only) - confirm `user_modified` stays false (or unlocked) and Tutor still has max_turns 100, CARD-444 clause, 7 skills.
4. Open Settings -> Preferences: find "Keep my agent customizations when platform packs update" (default ON). Same toggle on System & Software Updates card. **Do not turn it off on live data.**
5. Optional: `GET /api/agents/tutor/pack-content-backups` returns a list (may be empty until a forced reset).

---

## 5. Reply phrases

- Refine: say **continue**.
- Implement: say **build**.
- After proof: say **merge to qa**.
