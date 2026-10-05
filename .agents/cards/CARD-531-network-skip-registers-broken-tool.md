---
id: CARD-531
title: "A network-only sample-call skip lets a broken native tool register, and the Developer calls it 'ready for use'"
status: Done (Superseded by CARD-571)
completed: 2026-10-05
created: 2026-09-26
branch: qa
related:
  - CARD-511
  - CARD-520
  - CARD-523
labels:
  - type:bug
  - area:developer
  - area:tools
  - P2
needs_decision: none
milestone: M25
---

# [CARD-531] Registered without a test run: `get_weather` returns HTTP 400

> **Status**: Done (Superseded by CARD-571)
> **Related**: CARD-511 (register runs the tool once; skip allowed for secrets, network or side effects), CARD-523 (honest tool failures)
> **Labels**: `type:bug`, `area:developer`, `area:tools`, `P2`

## Evidence

- Session `d09a88dd-f6d0-4161-b41e-229ebfd4fceb`: Developer registered `get_weather` with `sample_call` skipped, `skip_reason` "requires network access to weather API". CARD-511 allows that; check status `checked_without_call`.
- The code uses keyless Open-Meteo but calls geocoding with `?city=Boston`. A keyless probe (`scratch\c520_weather_probe.py`) gets HTTP 400 "No value found at path 'name'"; `?name=Boston` works. So the tool fails on every call.
- The reply said the tool "is active and ready for use by the developer agent". It was registered with `grant_agent_ids: []`, so no agent can call it, and it does not work. (The missing grant is fixed by CARD-520 REQ-520-016; the false claim and the unverified run are this card.)

## Change (decide at refinement)

1. Allow a keyless, read-only network sample call (GET to a public host, short timeout) in the sandbox, or run it in a network-enabled sandbox; keep skip only for secrets and side effects.
2. When a tool is registered without a run, Tools Studio and the register result say "Registered without a test run" in plain words.
3. The Developer must not say "ready" for an unverified tool; its reply names the grant (which agents can call it) and whether a run passed.

## Done when

Re-registering the same `get_weather` code fails the sample call with the 400 (or passes once fixed); a skipped run is labelled; the Developer reply states grants and run status. Replay: Teach "weather in Boston" -> Ask Developer.

## Log

- 2026-09-29: battery triage: superseded by CARD-571: network-using tool code is never run at save, is saved as 'Not run: uses network, review before enabling', the model skip flag is gone, the Developer no longer registers tools, and Jacob enables each tool after reading its code
