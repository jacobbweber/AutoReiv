---
id: CARD-664
title: "Gaps API drops context_summary"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/web/test_card664_gap_context_summary.py]
branch: feat/card-664-gap-context-summary
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-08
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-663
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-664 Gaps API drops context_summary

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
`POST /api/agents/{id}/gaps` accepts a `context_summary` field, but the saved gap row does not keep it. Skill Studio gap drafts then only have the turn text for intent and lose the richer summary. Logged from the Oct 5 uncarded findings (findings list also has the 2026-10-03 CARD-522 note).

## Cause
The gaps router and/or the capability_gaps repository accept the field on input but do not persist or return it on the row.

## Change
Persist `context_summary` on the gap row and return it from the API so Skill Studio drafts can use it.

## What dies
Gap drafts that forget the summary the caller already sent.

## Proof
- Checks (failing first): posting a gap with `context_summary` stores it and a later read returns the same text; posting without it still works.
- No live journey required unless the UI path is broken too.

## Plan and decisions
Jacob approved the build on 2026-10-08.

## Root cause
The gap table had no `context_summary` column. `CapabilityGapRepository.create_gap` took the argument and dropped it, `get_gap` and `list_gaps` never selected it, and `CapabilityGap` had no field for it. The router used the summary only as model input for synthesis and never passed it on. The kernel already passes the reply as `context_summary` (lost the same way). Skill Studio's `gap_prefill.js` already reads `gap.context_summary`, so it always fell back to the turn text.

## Decisions
- New nullable `context_summary TEXT` column, in `INIT_SCHEMA_SQL` and in the create-table migration. Existing databases get it from `_migrate_if_missing` (an `ALTER TABLE ... ADD COLUMN`, the same pattern as the other added columns). Old rows keep their data and read `None`.
- `CapabilityGap.context_summary` is an optional field. The repository writes it (blank becomes `None`) and returns it from create, get and list through one shared column list and row mapper.
- `POST /api/agents/{id}/gaps` stores `context_summary`, falling back to `assistant_response` (the same fallback gap_prefill.js uses). With neither, it stores `None` and the request still works.

## Results
- New checks: `tests/unit/web/test_card664_gap_context_summary.py` covers the repository round trip, a gap without a summary, an old database gaining the column with its gaps kept, and the API (summary, reply only, neither; per-agent and all-agent lists). Before the fix: 4 failed (`CapabilityGap` has no `context_summary`; the API response had no such key). After: all pass.
- Existing gap tests (`test_gaps_api`, `test_capability_gaps`, the dogfood gap loop), the memory and core suites: 122 passed.
