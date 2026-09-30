---
id: CARD-543
title: "Developer can register a stub tool (\"real API integration pending\") that the agent then declines to use"
status: Superseded
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:bug
  - area:tools
  - P2
needs_decision: none
milestone: M25
---

# [CARD-543] Developer can register a stub tool ("real API integration pending") that the agent then declines to use

> **Status**: Superseded (2026-09-29 battery triage: superseded by CARD-571: the Developer no longer builds tools, and a Toolsmith-built tool (stub or not) stays disabled until Jacob reads the code in Tools Studio and enables it (D3))
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:bug`, `area:tools`, `P2`

## Why

CARD-539 live QA (card-520 journey, real vLLM): the Developer registered `get_weather` described as "Stub implementation; real API integration pending." The accepted skill runbook copied that text, so AutoReiv told the user the tool is a stub and did not call it. When asked explicitly, AutoReiv did call `get_weather` (scoping works; the call parked for approval).

## Change

The Developer's native-tool lane should either build a working tool (with a live check before register) or tell the operator plainly that it is a stub and not propose attaching it. Decide at refinement.

## Done when

A stub tool is never proposed for attachment without the operator being told; the card-520 journey's weather steps pass on desktop and phone.

## Log

- 2026-09-29: battery triage: superseded by CARD-571: the Developer no longer builds tools, and a Toolsmith-built tool (stub or not) stays disabled until Jacob reads the code in Tools Studio and enables it (D3)
