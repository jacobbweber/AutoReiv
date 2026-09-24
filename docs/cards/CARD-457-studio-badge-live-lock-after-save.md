---
id: CARD-457
title: "Studio platform badge should reflect a lock set by Save, not only the last sync"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-450
  - CARD-449
labels:
  - type:ux
  - area:packs
  - area:studio
  - P3
---

# [CARD-457] Studio platform badge should reflect a lock set by Save, not only the last sync

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-450 build on Jarvis (`feat/card-450-studio-platform-pack-reset`)
> **Labels**: `type:ux`, `area:packs`, `area:studio`, `P3`

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

If I edit a platform agent's system prompt in Agent Studio and save, Studio should tell me platform updates will now skip it. I shouldn't have to wait for a restart or a manual sync.

### Beat 2: What AutoReiv does now

1. The CARD-450 badge reads the **last sync report** (`GET /api/platform-packs/sync-status`), which only changes on boot, `POST /api/platform-packs/sync`, reset, or restore.
2. `PUT /api/agents/{id}` sets `user_modified` on a content edit (CARD-449 `should_set_content_lock`), but the report still shows the old status until the next sync.
3. `_public_agent` does not expose `user_modified`, so the UI cannot show the live lock.
4. When the global "Keep my agent customizations" setting is off (live on Jarvis 2026-09-24), every restart or sync force-resets edited platform agents. The Platform defaults section doesn't say so, so no badge ever appears and edits vanish on restart without a note in Agent Studio.

### Beat 3: What will change

1. Choose one: expose a plain `customized` flag on `GET /api/agents/{id}` for platform agents, or run a single-pack sync after a locking save (merge-safe since CARD-450).
2. The badge copy stays plain English.

### Beat 4: What dies today

A saved prompt edit that silently opts the agent out of platform updates, with no badge until the next restart.

---

## 2. Acceptance criteria (EARS)

- **[REQ-457-001]** WHEN an operator saves a content edit on a platform agent, THE Agent Studio badge SHALL show the skipped state without a restart or manual sync.
- ~~[REQ-457-003]~~ Moved into CARD-450 as REQ-450-011 (keep-customizations-off notice shipped there).
- **[REQ-457-002]** WHEN a save changes only max turns or model, THE SYSTEM SHALL NOT show a badge.
