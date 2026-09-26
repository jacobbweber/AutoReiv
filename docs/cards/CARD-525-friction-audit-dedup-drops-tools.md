---
id: CARD-525
title: "Friction audit drops recommendations: the dedup key has no tool name, so a second tool with the same problem (or in no skill) never gets a card"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-354
labels:
  - type:bug
  - area:observability
  - P3
---

# [CARD-525] Friction audit dedup drops recommendations for other tools

> **Status**: Ready (found in the CARD-520 reproduction on a scratch server, 2026-09-26 ~12:55 PM ET, qa `0f5cf9da`). P3: recommendations silently go missing; nothing breaks.
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
