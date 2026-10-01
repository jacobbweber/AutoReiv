---
id: CARD-546
title: "Out-of-domain routing and the Ask Developer button still depend on the model following the prompt"
status: Superseded
superseded_by: CARD-596
completed: 2026-10-01
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

> **Status**: Superseded by CARD-596 (2026-10-01: Jacob chose deliberate agent scopes and direct chat instead of routing)
> **Related**: CARD-539 (ADR-0061, D6)
> **Labels**: `type:bug`, `area:agents`, `P2`

## Why

CARD-539 live QA, journey `card-539-out-of-domain-routing`, real vLLM, 5 runs per viewport across the last commits: the Tutor due-review request was handed off in 6 of 10 runs. In the others AutoReiv answered itself, or stopped with "Execution terminated: Detected repetitive cycle calling tools" after looping on `wiki_note_search`. For the flight-booking request, the Ask Developer button appeared only when the reply used those words (2 of 5 runs that reached the step). The other replies said plainly that the request was out of scope and suggested a travel site.

Evidence: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-539-final3\` (both steps pass on phone) and `card-539-final4\` (desktop step 2 and phone step 1 fail).

## Change (design, decide at refinement)

Make the fallback structural instead of worded. For example, show Ask Developer on any turn where `lookup_agents` ran and no handoff followed, or run a router check before the turn for requests that match no ticked skill. Keep the no-refusal rule.

## Done when

The routing journey passes 5 of 5 runs on desktop and phone with the real model.

## Re-measure (Jacob class-b, 2026-09-30, ~2:05-2:55 PM ET)

Throwaway :8770, clone of real data, qa `de12b988`-era code, AutoReiv on `default` = **nemotron-3.5-lightning** (262k), approval mode ask. Prompt: the journey's due-review ask ("Start my flashcard due review for today: show me the first card that is due and grade my answer."). Driver `scratch/live_546_tutor.py`, results `scratch/live_546_results_*.json`.

| Batch | Handed to Tutor | Notes |
|---|---|---|
| A: 10 runs, one env | **1/10** | Run 1 handed off. From run 3 on, AutoReiv answered from memory facts saved after run 1 (`user.flashcard_review_due_today: false`, no tools) - the runs are not independent, so this batch overstates the miss rate. |
| B: 10 runs, fresh clone before each | **2/10** | Runs 4 and 7 handed off (lookup_agents -> inspect_agent -> handoff_to_agent -> Tutor). The 8 misses never called `lookup_agents`; they searched the wiki / system health and replied "no flashcards found" (one said it could not reach the education tools). No loop stops, no refusal wording. |

**Finding:** routing is worse than the 6/10 of 2026-09-26 and depends on the model choosing `lookup_agents` first. Once it does, the handoff follows every time (2/2). This supports the structural fix in "Change": a router check before the turn for requests that match none of AutoReiv's ticked skills (or offer the Tutor button whenever education tools are named but not ticked). Also: post-turn memory extraction can freeze a wrong "state" fact after one run - worth a separate look.

## What we learned (closing note, 2026-10-01)

- Baseline on nemotron-3.5-lightning: AutoReiv handed study requests to Tutor in 2/10 runs; in 8/10 it never called `lookup_agents` and ran 15-43 wiki tools instead (when it looked, the hand-off always followed).
- An overlapping skill confused routing: AutoReiv also ticked `socratic-tutoring`, so its domain line (and a router) claimed study requests.
- A prompt hint ("hand it off now") did not help (2/10); a routing check before the turn plus a platform-made hand-off reached 8/10.
- Saved short-lived memory facts replaced live checks (CARD-597).
- Jacob's decision (2026-10-01): no routing; agents get deliberate scopes and the user picks the agent (CARD-596). The design branch and prototype were deleted.

## Log

- 2026-09-29: battery triage: still valid; Ask Developer buttons now open Toolsmith (CARD-571); routing in the battery followed the prompt (Developer and Toolsmith handed off correctly on Spark/Nimo)
- 2026-09-30: re-measured on nemotron per Jacob's class-b approval: Tutor handoff 2/10 (fresh env each run), 1/10 (shared env, memory-contaminated). Still Ready; the structural router fix is the next step.
- 2026-10-01: Superseded by CARD-596 (agent scopes and direct chat); design branch card/546-routing-design deleted.
