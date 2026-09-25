---
id: CARD-501
title: "Smoke: first click on a reply button right after sending (focused composer) must land"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-472
  - CARD-465
  - CARD-470
labels:
  - type:test
  - area:chat
  - area:frontend
  - P3
---

# [CARD-501] Smoke: first click on a reply button right after sending must land

> **Status**: Ready
> **Created**: 2026-09-25 (found while building CARD-472)
> **Related**: CARD-472, CARD-465 (composer grows on focus), CARD-470 (`pressRegions`)
> **Labels**: `type:test`, `area:chat`, `area:frontend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** Right after a reply arrives, the first click on View Full Report, Workbench or Copy works.

**Beat 2: What AutoReiv does now.** CARD-472 found that on desktop the focused composer (grown to about 160 px) shrank on the mousedown of a click in the message list; the pinned list shifted and the click was lost. CARD-472 added `messagesContainer` to `pressRegions` (commit `87e1ab2a`), proven with the scratch repro `scratch/c472_dbg.cjs` (0 fetches before, 1 after) and a source guard. The smoke fixture (3 short messages) could not reproduce the shift, so there is no end-to-end test.

**Beat 3: What will change.** A smoke case that sends a real turn through the fake gateway (long reply ending in an `artifact://` link, list pinned to bottom, composer focused), then clicks View Full Report once and expects the Workbench to open. Desktop and phone. Must be red with `messagesContainer` removed from `pressRegions`.

**Beat 4: What dies.** Guard-only coverage for this path.

## 2. Acceptance criteria (EARS)

- **[REQ-501-001]** WHEN a reply has just arrived and the composer is focused, THE first click on a reply's View Full Report SHALL open the Workbench (desktop and phone).

## 3. Tests

Smoke TC-35 desktop + phone. Confirm red by temporarily reverting `87e1ab2a`.

## 4. Runbook

Send a message that produces a report link; without clicking elsewhere, click View Full Report once. The Workbench opens.
