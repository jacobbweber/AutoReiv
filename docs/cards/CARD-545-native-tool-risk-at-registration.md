---
id: CARD-545
title: "Native tools declare risk at registration (ADR-0061 D11, full)"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:feature
  - area:tools
  - P3
---

# [CARD-545] Native tools declare risk at registration (ADR-0061 D11, full)

> **Status**: Ready (filed from CARD-539, 2026-09-26 ~11:10 PM ET).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:feature`, `area:tools`, `P3`

## Why

CARD-539 took D11 as recommended but kept the existing policy for tools with no declared risk. A read-only tool such as `get_weather` built by the Developer therefore asks for approval on every call (live QA: `approval_required` on the first call).

## Change

`register_native_tool` records `risk` (read_only / write / network / destructive); read-only tools run without confirmation, others default to `require_confirm`; operator `tool_policy` still overrides. Generated skills copy the tool's risk into frontmatter.

## Done when

A read-only native tool runs without an approval card; a write tool still asks; unit tests cover both.
