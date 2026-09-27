---
id: CARD-543
title: "Developer can register a stub tool (\"real API integration pending\") that the agent then declines to use"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:bug
  - area:tools
  - P2
---

# [CARD-543] Developer can register a stub tool ("real API integration pending") that the agent then declines to use

> **Status**: Ready (filed from CARD-539, 2026-09-26 ~11:10 PM ET).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:bug`, `area:tools`, `P2`

## Why

CARD-539 live QA (card-520 journey, real vLLM): the Developer registered `get_weather` described as "Stub implementation; real API integration pending." The accepted skill runbook copied that text, so AutoReiv told the user the tool is a stub and did not call it. When asked explicitly, AutoReiv did call `get_weather` (scoping works; the call parked for approval).

## Change

The Developer's native-tool lane should either build a working tool (with a live check before register) or tell the operator plainly that it is a stub and not propose attaching it. Decide at refinement.

## Done when

A stub tool is never proposed for attachment without the operator being told; the card-520 journey's weather steps pass on desktop and phone.
