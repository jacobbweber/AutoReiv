---
id: CARD-458
title: "Single-pack promotion overwrites lock-migration report; restore gaps"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-450
  - CARD-449
labels:
  - type:bug
  - area:packs
  - P3
---

# [CARD-458] Single-pack promotion overwrites lock-migration report; restore gaps

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-450 build on Jarvis (`feat/card-450-studio-platform-pack-reset`)
> **Labels**: `type:bug`, `area:packs`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine scope - **still no product code** |
| **`build`** | Implement this card test-first |
| **`merge to qa`** | After the acceptance criteria are proven |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

Resetting or restoring one agent must not erase other agents' diagnostics. A restore should bring back what the dialog says it brings back, and nothing surprising later.

### Beat 2: What AutoReiv does now

1. CARD-450 merges single-pack results into `platform_pack_sync_last_report`. But `migrate_false_content_locks` still overwrites `platform_pack_lock_migration_report` with only the subset's results, so `lock_migration` in sync-status loses other packs after a reset or restore.
2. Reset clears the pack's turned-off-skills record (`platform_operator_disabled_skills`), and restore does not bring it back. A restored agent that later unlocks (prompt back at baseline) would get those skills turned on again by promotion.
3. Backups snapshot only database fields. Skill files and the AppData `pack.json` projection are not backed up, and the restore dialog says so.

### Beat 3: What will change

1. Merge the subset lock-migration results the same way as REQ-450-010.
2. Store the turned-off-skills list in the backup and restore it.
3. Decide with Jacob whether skill-file snapshots are worth it (probably not; platform files are reproducible).

### Beat 4: What dies today

Reset or restore on one agent wiping other agents' lock-migration diagnostics.

---

## 2. Acceptance criteria (EARS)

- **[REQ-458-001]** WHEN promotion runs for a `pack_ids` subset, THE SYSTEM SHALL keep other packs' entries in the lock-migration report.
- **[REQ-458-002]** WHEN a backup taken before reset is restored, THE SYSTEM SHALL restore that pack's turned-off-skills record.
