---
id: CARD-546
title: "Out-of-domain routing and the Ask Developer button still depend on the model following the prompt"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:bug
  - area:agents
  - P2
needs_decision: none
milestone: M25
---

# [CARD-546] Out-of-domain routing still depends on the model following the prompt

> **Status**: Ready (filed from CARD-539 live QA, 2026-09-26 ~11:55 PM ET).
> **Related**: CARD-539 (ADR-0061, D6)
> **Labels**: `type:bug`, `area:agents`, `P2`

## Why

CARD-539 live QA, journey `card-539-out-of-domain-routing`, real vLLM, 5 runs per viewport across the last commits: the Tutor due-review request was handed off in 6 of 10 runs. In the others AutoReiv answered itself, or stopped with "Execution terminated: Detected repetitive cycle calling tools" after looping on `wiki_note_search`. For the flight-booking request, the Ask Developer button appeared only when the reply used those words (2 of 5 runs that reached the step). The other replies said plainly that the request was out of scope and suggested a travel site.

Evidence: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-539-final3\` (both steps pass on phone) and `card-539-final4\` (desktop step 2 and phone step 1 fail).

## Change (design, decide at refinement)

Make the fallback structural instead of worded. For example, show Ask Developer on any turn where `lookup_agents` ran and no handoff followed, or run a router check before the turn for requests that match no ticked skill. Keep the no-refusal rule.

## Done when

The routing journey passes 5 of 5 runs on desktop and phone with the real model.

## Log

- 2026-09-29: battery triage: still valid; Ask Developer buttons now open Toolsmith (CARD-571); routing in the battery followed the prompt (Developer and Toolsmith handed off correctly on Spark/Nimo)
