---
id: CARD-542
title: "Own-skill search when an agent ticks more than 20 skills (ADR-0061 D9)"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:feature
  - area:agents
  - P3
---

# [CARD-542] Own-skill search when an agent ticks more than 20 skills (ADR-0061 D9)

> **Status**: Ready (filed from CARD-539, 2026-09-26 ~11:10 PM ET).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:feature`, `area:agents`, `P3`

## Why

CARD-539 D9 said a `skill_search` over the agent's own ticked skills replaces the skill index when it gets large. No agent is near 20 ticks today (AutoReiv 13-14), so CARD-539 kept the full index.

## Change

Above 20 ticked skills, replace the rendered skill index with a one-line pointer and a `skill_search` tool that searches only the agent's ticked skills; never foreign skills.

## Done when

An agent with 21+ ticks gets the search tool and a short index; results never include unticked skills (unit test).
