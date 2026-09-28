---
id: CARD-540
title: "Drop the inert allow_wiki_access agent field"
status: Done
created: 2026-09-26
branch: feat/card-562-developer-one-card-to-in-review
related:
  - CARD-539
labels:
  - type:chore
  - area:agents
  - P3
needs_decision: none
milestone: M25
completed: 2026-09-28
---

# [CARD-540] Drop the inert allow_wiki_access agent field

> **Status**: Done (absorbed by CARD-562, merged to qa 2026-09-28).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:chore`, `area:agents`, `P3`

## Why

CARD-539 removed `allow_wiki_access` enforcement: wiki tools reach an agent only through ticked wiki skills (ADR-0061). The field is still stored in `AgentProfile` / guardrails / Settings and shown nowhere that matters, so it reads like a permission that does nothing.

## Change

Remove the field from models, guardrails, settings payloads and the SQLite column (migration drops or ignores it); remove any leftover UI text.

## Done when

No code reads or writes `allow_wiki_access`; a unit test asserts wiki tools follow ticks only; old profiles with the field still load.

## Results
Absorbed and done in CARD-562 (2026-09-28): field removed from AgentProfile, AgentCustomization, pack schema, guardrails, registry override, settings repo and the agents router; old profiles/packs that still carry it load (ignored). Test: tests/unit/agents/test_card540_no_wiki_access_field.py.
