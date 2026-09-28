---
id: CARD-540
title: "Drop the inert allow_wiki_access agent field"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:chore
  - area:agents
  - P3
needs_decision: none
milestone: M25
---

# [CARD-540] Drop the inert allow_wiki_access agent field

> **Status**: Ready (filed from CARD-539, 2026-09-26 ~11:10 PM ET).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:chore`, `area:agents`, `P3`

## Why

CARD-539 removed `allow_wiki_access` enforcement: wiki tools reach an agent only through ticked wiki skills (ADR-0061). The field is still stored in `AgentProfile` / guardrails / Settings and shown nowhere that matters, so it reads like a permission that does nothing.

## Change

Remove the field from models, guardrails, settings payloads and the SQLite column (migration drops or ignores it); remove any leftover UI text.

## Done when

No code reads or writes `allow_wiki_access`; a unit test asserts wiki tools follow ticks only; old profiles with the field still load.
