---
id: CARD-544
title: "Decide whether AutoReiv should keep the coding skill ticked (code work vs hand off to Developer)"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:decision
  - area:agents
  - P3
---

# [CARD-544] Decide whether AutoReiv should keep the coding skill ticked (code work vs hand off to Developer)

> **Status**: Ready (filed from CARD-539, 2026-09-26 ~11:10 PM ET).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:decision`, `area:agents`, `P3`

## Why

CARD-539 section 9.2 assumed a code request to AutoReiv hands off to Developer. The seeded AutoReiv pack ticks `coding` (repo_file_read/list/write/patch), so under ADR-0061 a code request is in its domain: live QA saw AutoReiv plan a job and ask approval for `repo_file_write` itself. The routing journey now probes with a Tutor due-review request instead (handed off on desktop and phone).

## Change

Product decision for Jacob: keep `coding` on AutoReiv, or untick it (seed change) so code requests route to Developer.

## Done when

Decision recorded; seed pack and the routing journey match it.
