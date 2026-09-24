---
id: CARD-459
title: "Serve bootstraps twice; second platform-pack run overwrites the boot report"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-450
  - CARD-443
  - CARD-455
labels:
  - type:bug
  - area:packs
  - area:serve
  - P2
---

# [CARD-459] Serve bootstraps twice; second platform-pack run overwrites the boot report

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-450 live test on Jarvis (6:32 PM ET restart)
> **Labels**: `type:bug`, `area:packs`, `area:serve`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine approach - **still no product code** |
| **`build`** | Make serve bootstrap once, test-first |
| **`merge to qa`** | After a restart shows one promotion run and an honest boot report |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

After a restart, sync-status must say what actually happened at boot. If Developer was force-reset, the report should say so, not `unchanged`.

### Beat 2: What AutoReiv does now

1. `src/cli/main.py` serve runs `uvicorn.run("src.web.app:create_app", factory=True)`.
2. Importing `src.web.app` runs module-level `app = create_app()` (line ~650). The factory then calls `create_app()` again. That means two full bootstraps per serve start: registries, platform-pack promotion, schedulers.
3. Live 6:32 PM ET: the first run force-reset Developer (backup at 22:32:03 UTC, keep-customizations off). The second run, one second later, reported `unchanged` and overwrote `platform_pack_sync_last_report` and the lock-migration report.
4. Tests (`from src.web.app import app`, CARD-455) and Playwright (`src.web.app:app`) depend on the module-level app.

### Beat 3: What will change

1. Serve bootstraps once: either serve the module-level app or make the module-level app lazy. Keep test and Playwright entry points working.
2. Optional: keep a short boot history, or never let a no-op run overwrite a report that recorded a reset.

### Beat 4: What dies today

Double boot work, and a boot report that hides force resets.

---

## 2. Acceptance criteria (EARS)

- **[REQ-459-001]** WHEN serve starts, THE SYSTEM SHALL run platform-pack promotion exactly once.
- **[REQ-459-002]** WHEN a boot force-resets a pack, THE sync-status report after startup SHALL show `force_reset` for that pack.
