---
id: CARD-534
title: "A resumed job phase runs its model turn on the parent chat session instead of its ::phase:: session"
status: Done (Superseded by CARD-548)
completed: 2026-10-05
created: 2026-09-26
branch: qa
related:
  - CARD-530
  - CARD-219
  - CARD-259
labels:
  - type:bug
  - area:jobs
  - P3
superseded_by: CARD-548
needs_decision: none
---

# [CARD-534] Resumed phase turns land in the parent session

> **Status**: Done (Superseded by CARD-548)
> **Related**: CARD-530, CARD-219 (resume an open job), CARD-259 (kill/resume)
> **Labels**: `type:bug`, `area:jobs`, `P3`

## Evidence

- A phase's first run uses `_ensure_phase_session` (`<session>::phase::<phase_id>`), so its model turns and tool results live there.
- The resume path in `routers/chat.py` (~L1930, "Resume an open multi-phase job") calls `_stream_turn_bound(session_id=req.session_id, ...)`: the resumed turn reads and writes the **parent** session. It does not see the phase session's earlier tool calls, and its own tool calls appear in the parent chat.
- Seen in Jacob's `job_3bdef1802655` (register_native_tool calls in session `d09a88dd-...`, not in `...::phase::phase_4298aa95cc81`) and in the CARD-530 scratch repro (`job_8edb14d8c1c2`).

## Change (decide at refinement)

Resume a phase on its own phase session (same as the first run), and surface only the phase outcome in the parent, as on the first run. Check CARD-219/259 tests and the Stop-then-resume path.

## Done when

A Stop-then-resume or HITL resume keeps all of a phase's turns in its `::phase::` session; the parent shows the same summary as an uninterrupted run.
