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
needs_decision: none
milestone: M25
---

# [CARD-541] Drop platform pack.json allowed_tool_names / pack_tool_names

> **Status**: Ready, partly done in CARD-562 (2026-09-28); the remainder is tracked in docs/findings.md.
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:chore`, `area:agents`, `P3`

## Why

After CARD-539 an agent's tools come only from `resolve_allowed_tools` (REQUIRED_PLATFORM_TOOLS + tools of ticked skills). Platform `pack.json` files still carry `allowed_tool_names` / `pack_tool_names`, kept as read-only compat; they grant nothing and can drift from the real set.

## Change

Also replace the Tutor pack's fixed "Focus strictly on ..." domain sentence with a pointer to the generated domain line (D5; CARD-539 did this for AutoReiv only). Remove the fields from the shipped platform packs and from the pack schema/export (import still tolerates and ignores them); update the pack linter.

## Done when

Shipped packs have no tool lists; import of an old pack with tool lists ignores them with a note; the per-agent agreement test still passes.

## Results (partial)
CARD-562 (merged to qa 2026-09-28) removed `pack_tool_names` from the Developer pack; the Tutor fixed-domain sentence was already replaced in CARD-537. Remaining: the autoreiv, direct and tutor packs plus the pack schema/export/linter (about 170 references in 61 files); tracked in docs/findings.md (2026-09-28).
