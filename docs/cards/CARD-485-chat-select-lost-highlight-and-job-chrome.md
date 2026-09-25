---
id: CARD-485
title: "Picking a chat doesn't move the list highlight or restore its job strip and running-turn status (lost in the CARD-397 split)"
status: Done
created: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-476
  - CARD-473
  - CARD-466
  - CARD-471
  - CARD-486
  - CARD-487
  - CARD-488
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P3
---

# [CARD-485] Picking a chat doesn't move the list highlight or restore its job strip and running-turn status (lost in the CARD-397 split)

> **Status**: Done (merged to qa 2026-09-25 ET per Jacob's "merge to qa")
| pytest tests/integration | 107 pass | |
| ruff | 9 findings (baseline) | CARD-454 |

**Repro (`scratch/c485_repro.cjs`, fresh `scripts/smoke_server.py --port 8767`, no AppData), desktop and phone:**
- highlight moves to the picked chat `[false,false,true]`;
- the drawer closes;
- 1 `/journey` and 1 `/status` request on select, and on load too;
- job strip visible, 1 inline chrome block;
- Stop shown and Send hidden while status says running.

**Notes:**
- As before the split, a chat whose job is finished also shows its strip (DONE) and phase chips when opened.
- Stop while a reply runs elsewhere doesn't stop it yet: CARD-486.
- Switching chats while your own reply streams keeps showing the old chat and blocks sending (same before the split): CARD-488.

---

## Merge note (2026-09-25 ET)

Jacob said **merge to qa**. `feat/card-485-session-select-restore` merged `--no-ff` into qa and pushed; branch deleted. Post-merge test results are in the merge report. Follow-ups: CARD-486 (Stop, including busy-elsewhere), CARD-488, CARD-487, CARD-473 (reuse `watchSessionStatus`).
