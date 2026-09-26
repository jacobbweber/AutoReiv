---
id: CARD-513
title: "steering/product.md and structure.md still describe \"7 studios\" and miss Skill, Tools, Education, Projects and Prompts"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-496
labels:
  - type:docs
  - area:docs
  - P3
---

# [CARD-513] Steering docs describe a stale "7 studios" set

> **Status**: Ready (found while amending `steering/product.md` for CARD-495, 2026-09-25 ET). Not next: docs drift only, no data risk. The queue is Factory retirement CARD-495, CARD-496, CARD-511, CARD-497, CARD-512, CARD-498, then Education Studio.
> **Related**: CARD-495 (fixed only the Factory lines), CARD-496 (removes `#view-factory`)
> **Labels**: `type:docs`, `area:docs`, `P3`

## Problem

- `steering/product.md` L21 is headed "The 7 Integrated Web Studios". It has sections for Chat, Routines, Observability, Agent Studio, Settings, Docs (not shipped) and Wiki, but none for Skill Studio, Tools Studio, Education Studio, Projects or Prompts.
- `templates/index.html` on qa `7a6ea31b` has views for agents, chat, education, factory (retiring), lumina, observability, projects, prompts, routines, settings, skill-studio, tools-studio and wiki.
- `steering/structure.md` L48 says "7-studio architecture", and L41's studio list misses education, projects and prompts.

## Change

Rewrite the studio section of `product.md` from the real view list after CARD-496 lands, one short entry per studio. Update `structure.md` L41 and L48 to match. Docs only.

## Done when

Every shipped `#view-*` has one entry in `product.md`; no retired studio is listed; `structure.md` matches.
