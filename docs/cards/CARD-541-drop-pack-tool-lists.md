---
id: CARD-541
title: "Drop platform pack.json allowed_tool_names / pack_tool_names; no fixed domain text in packs"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:chore
  - area:agents
  - P3
---

# [CARD-541] Drop platform pack.json allowed_tool_names / pack_tool_names

> **Status**: Ready (filed from CARD-539, 2026-09-26 ~11:10 PM ET).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:chore`, `area:agents`, `P3`

## Why

After CARD-539 an agent's tools come only from `resolve_allowed_tools` (REQUIRED_PLATFORM_TOOLS + tools of ticked skills). Platform `pack.json` files still carry `allowed_tool_names` / `pack_tool_names`, kept as read-only compat; they grant nothing and can drift from the real set.

## Change

Also replace the Tutor pack's fixed "Focus strictly on ..." domain sentence with a pointer to the generated domain line (D5; CARD-539 did this for AutoReiv only). Remove the fields from the shipped platform packs and from the pack schema/export (import still tolerates and ignores them); update the pack linter.

## Done when

Shipped packs have no tool lists; import of an old pack with tool lists ignores them with a note; the per-agent agreement test still passes.
