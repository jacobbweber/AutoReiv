---
id: CARD-547
title: "Developer job strip shows Job failed next to a DONE phase while an attach proposal waits"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
  - CARD-530
labels:
  - type:bug
  - area:chat
  - P3
---

# [CARD-547] Job strip shows Job failed next to a DONE phase

> **Status**: Ready (filed from CARD-539 live QA, 2026-09-26 ~11:55 PM ET).
> **Related**: CARD-539, CARD-530
> **Labels**: `type:bug`, `area:chat`, `P3`

## Evidence

In the card-520 journey (desktop, step 4), the Developer chat's job strip read "Job failed | job_e6e4a6a42b73 | Phase 2/2 Execute | developer | DONE" while the `attach_tool_to_skill` approval card was waiting. CARD-530 says a failed job never shows DONE. Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-539-final3\card-520-teach-needs-tool-desktop-04-the-developer-builds-the-tool-and-proposes-attac.png`.

## Change

Find out why the job ends failed after its phase completes (possibly the CARD-535 nudge flow), then make the strip consistent: a failed job shows FAILED with the reason.

## Done when

Step 4 of the card-520 journey shows a consistent strip, and a unit test covers the failed-after-DONE case.