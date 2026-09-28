---
id: CARD-565
title: "A chat message that mentions acceptance criteria stays a normal turn"
type: bug
status: Ready
priority: P1
milestone: M24
needs_decision: none
proof:
  journeys: [card-565-acceptance-criteria-routes-to-job]
  checks: [tests/unit/orchestration/test_card565_criteria_reference_stays_react.py]
branch: fix/card-565-acceptance-criteria-routes-to-job
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-28
---


# CARD-565 A chat message that mentions acceptance criteria stays a normal turn

## Problem
In Chat, "Review CARD-3 against its acceptance criteria and record your verdict." to Architect did not run as a normal
turn: it became a two-phase standing Job (Formulate in one session, Execute in another), so the review tools ran in
phase sessions and the Architect chat only got relayed text. Seen live in CARD-564 round 1. Any ordinary message that
merely mentions a card's "acceptance criteria" (or "success criteria") is diverted the same way.

## Cause
`route_standing_chat` (src/application/orchestration/standing_job_graph.py) sends a message to the Job graph when
`is_outcome_shaped` matches. `_GOAL_DELIVERABLE` in src/application/orchestration/outcome_intake.py treats the bare phrases
`acceptance criteria` and `success criteria|rule|condition` anywhere in a 40+ character message as goal/deliverable
language (CARD-230). The intended trigger is an ask that states its own deliverable and testable stop rule
(deliver/produce X, "done when: ...", wiki writes, first/then/finally steps); a reference to someone else's criteria is not that.

## Change
In `_GOAL_DELIVERABLE`, `acceptance criteria` and `success criteria|rule|condition` count only when the message states them
(followed by `:` or `-`, e.g. "acceptance criteria: the note exists"), not when it refers to them ("against its acceptance
criteria", "the card's success criteria"). `done when`, `success when`, deliverable verbs, wiki writes and multi-step markers
are unchanged. How standing Jobs start (runtime routing, no toggle, CARD-230/271) is unchanged.

## What dies
Routing a message into a standing Job only because it mentions acceptance or success criteria.

## Proof
- Journey `card-565-acceptance-criteria-routes-to-job` (live QA, Architect on the Spark reasoning default): throwaway repo
  with CARD-3 In Review on its card branch; "Please review CARD-3 against its acceptance criteria and record your verdict."
  runs review_card and finish_review in the Architect session itself, with no Formulate/Execute phase text in the chat.
- Checks: `test_card565_criteria_reference_stays_react.py`: references ("against its acceptance criteria", "check the card's
  success criteria") route SHORT_REACT (failing first); stated criteria ("Build X. Acceptance criteria: ...", "success criteria:
  ...") and the existing CARD-230/236/271 job asks still route MULTI_STEP_JOB_GRAPH.

## Plan and decisions
Narrow fix inside the existing design (runtime decides, CARD-230/271): only the two over-broad phrases change. Replacing
keyword routing with an explicit Jobs trigger would change how standing Jobs start (product decision) and is not in this card.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-565\...`

## Release note
CARD-565: a chat message that only mentions acceptance or success criteria (e.g. "review CARD-3 against its acceptance criteria") stays a normal turn instead of becoming a two-phase standing Job.
