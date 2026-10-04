---
id: CARD-525
title: "Friction audit drops recommendations: the dedup key has no tool name, so a second tool with the same problem (or in no skill) never gets a card"
status: Done
completed: 2026-10-04
created: 2026-09-26
branch: feat/card-525-527-545-friction-dedup-builtin-native-risk
related:
  - CARD-520
  - CARD-354
labels:
  - type:bug
  - area:observability
  - P3
needs_decision: none
milestone: M25
---

# [CARD-525] Friction audit dedup drops recommendations for other tools

> **Status**: Done (2026-10-04, merged to qa from `feat/card-525-527-545-friction-dedup-builtin-native-risk`). Found in the CARD-520 reproduction, 2026-09-26.
> **Related**: CARD-520 (tool escalation rename; decision D11 keeps this separate), CARD-354 (friction auditor)
> **Labels**: `type:bug`, `area:observability`, `P3`

## Evidence

- Scratch server, fresh data `scratch\c520_repro`, script `scratch\c520_repro.py`: one session with four 20,790-byte tool results (`c520_inventory_dump`, `c520_other_dump`, `wiki_note_read`, `wiki_note_search`). The audit reported **4 incidents, 3 recommendations**. `c520_other_dump` got none.
- Cause: `telemetry_friction_auditor.py` L46-63 dedups on `(agent_id, skill_path, friction_type)`. Both unknown tools have `skill_path: None` and `payload_bloat`, so the second collides with the first. Two tools in the same skill with the same problem also collide (only the first gets a card).
- The key is built from **every** existing skill proposal, including dismissed and applied ones, so after one payload-bloat card for a skill (or for "no skill") the audit never raises another for that agent, even for a different tool, months later.

## Change

- Dedup on `(agent_id, tool_name, friction_type)` (CARD-520 adds `tool_name` to `RunbookRecommendation`; fall back to parsing the old text for old records).
- Only pending (draft) and escalated recommendations block a new one; dismissed ones block for a cool-down (for example 7 days) instead of forever. Decide the cool-down at refinement.

## Done when

Two different tools with the same friction each get a recommendation; the same tool does not get a duplicate while one is pending or escalated; a dismissed one can come back after the cool-down. Tests: auditor unit tests for the three cases.

## Built (2026-10-04)
- The dedup key is `(agent_id, tool_name, friction_type)` (`src/domain/observability/friction_dedup.py`). Old records without `tool_name` get it from their text (`Escalate <tool> to`), else fall back to `skill:<skill_path>`.
- Only pending and escalated recommendations block a new one. Dismissed and applied ones block for a cool-down after the decision (proposal `updated_at`): 7 days, or routine metadata `dismissed_cooldown_days`.
- The audit reads up to 2000 staged proposals (it read the default 100, so older cards stopped counting).
- The Observability router reuses the same text parser and status mapping.

## Plan and decisions
- D1: cool-down 7 days (the card's example), overridable per routine.
- D2 (product decision, taken): an **applied** patch also waits out the cool-down instead of unblocking at once. The audit looks back 24 h, so it would re-raise the same pre-fix calls straight after Apply. After the cool-down, a problem that is still there comes back.

## Results
| Check | Result | Notes |
|---|---|---|
| Unit: two unmapped tools, two tools in one skill, same tool twice | PASS | `tests/unit/routines/test_card525_friction_dedup.py` (10 tests) |
| Unit: no duplicate while pending/escalated; dismissed returns after cool-down; metadata cool-down; applied cool-down; per agent | PASS | same file |
| Live :8770 (seeded session, real audit route) | PASS | 6 oversized tool results -> 6 cards (the old key gives 3: two pairs collided); rerun -> 0 new; after Dismiss (c525_alpha_dump) and Apply (get_recent_errors) a rerun -> 0 (cool-down) |
| Screenshot | PASS | `autoreiv-qa\ui1003l\525-friction-two-unmapped-tools-desktop.png` (c525_alpha_dump and c525_beta_dump each have a card) |

The friction sessions were seeded (oversized tool messages written to the :8770 DB). These checks used the API and UI with no model call (Spark Nemotron returned no token between 12:52 and 1:11 AM ET on 2026-10-04; :8770 was configured for it from the start).

## Findings
- None new.

## Release note
The telemetry audit gives each tool its own recommendation. A dismissed or applied one can come back after 7 days if the problem is still there.

Full suite on `9d13b9ae`: pytest 2502 passed / 12 skipped; preflight GREEN (vitest 1052, smoke 83/83).
