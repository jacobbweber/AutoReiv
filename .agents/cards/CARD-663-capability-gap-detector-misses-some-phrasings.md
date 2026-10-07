---
id: CARD-663
title: "Capability-gap detector misses some phrasings"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed:
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-663 Capability-gap detector misses some phrasings

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
When an agent says it lacks a tool using some wordings (for example "I do not have a direct email-sending tool"), the capability-gap detector does not file a gap. Those gaps are then missing from Agent Studio / Skill Studio even though the reply told the operator the capability is missing. Logged from the Oct 5 uncarded findings (findings list also has the 2026-10-03 CARD-615 note).

## Cause
`CapabilityDetector` (and related reply rules) only match some phrasings. After CARD-615, reply rules gained their own "lacks tool" check for the Ask Developer line, but the detector that files gaps was left unchanged.

## Change
Widen the detector (or share one matcher with reply rules) so the known missed phrasings file a gap the same way the clearer ones do. Keep false positives low.

## What dies
Silent misses where the model admits a missing tool but no gap row is created.

## Proof
- Checks (failing first): each known missed phrasing from the findings produces a gap; a reply that does not admit a missing tool still does not.
- Live or journey only if the unit bar is not enough.

## Plan and decisions
Needs Jacob's build approval before any work starts. Prefer one shared matcher used by both the detector and the Ask Developer line so they cannot drift again.
