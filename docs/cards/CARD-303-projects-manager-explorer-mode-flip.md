# [CARD-303] Projects Manager / Artifact Explorer mode flip

> **Status**: In Review  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: Jacob review + Architect lock (two-button flip)
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Overlay drawer still fell behind Artifact Explorer. Jacob leans two dedicated full views for consistency and space.

## 2. What to Build
Two studio modes in chrome: **Projects Manager** (browse/Set Active/Create/Align) and **Artifact Explorer** (live tree + drift for Active). Default = last Active Explorer. No overlay stacking.

## 3. Acceptance Criteria
- [x] Two mode buttons; only one full panel visible
- [x] Manager never sits under Explorer
- [x] Default opens Artifact Explorer when an Active project exists
- [x] Set Active switches into Explorer with live tree
- [x] Vitest for mode chrome

## Design lock
Two-button flip; dedicated space per job.
