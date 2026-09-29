---
id: CARD-535
title: "After approving a propose_* draft once the reply has ended, the Developer does not continue"
status: Done
completed: 2026-09-29
created: 2026-09-26
branch: qa
related:
  - CARD-530
  - CARD-472
labels:
  - type:bug
  - area:chat
  - area:hitl
  - P2
needs_decision: none
milestone: M24
---

# [CARD-535] Approving a draft does not make the Developer continue

> **Status**: Done (closed in CARD-577). Obsolete: Developer has no propose_* tools since CARD-562 and Toolsmith builds tools directly (register_native_tool), so the approve-then-continue flow this card describes no longer exists.
> **Related**: CARD-530 (D1: approving a `propose_*` draft only records the decision), CARD-472
> **Labels**: `type:bug`, `area:chat`, `area:hitl`, `P2`

## Evidence

- CARD-530 D1: approving a `propose_*` draft saves one "Approved: ..." note and returns `resume_chat: false`, so no second stream starts (that fixed the kill-and-resume bug).
- Live repro on scratch 8767 (real vLLM): the Developer ended its turn with "Wait for human approval" after `propose_tool`, and never registered the tool after the approval. Execute then filed a second draft (`appr_5a49cac34388`) that stayed pending.
- Browser check (phone): after the job finished Done, a second `propose_tool` approval card was still showing in the chat.

## Change (decide at refinement)

When a `propose_*` draft is approved and the chat is idle, offer a "Continue" action (or send one continue turn automatically once idle). Consider not filing a second identical draft in Execute when Formulate's draft is already approved or pending.

## Done when

Approving a draft after the reply has ended lets the Developer carry on (one click at most), with no second stream while a reply is live and no duplicate draft cards.

## Log
- 2026-09-29: Closed in CARD-577. Obsolete: Developer has no propose_* tools since CARD-562 and Toolsmith builds tools directly (register_native_tool), so the approve-then-continue flow this card describes no longer exists.
