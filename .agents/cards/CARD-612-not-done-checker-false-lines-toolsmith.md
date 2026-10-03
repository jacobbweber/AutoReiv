---
id: CARD-612
title: "The CARD-599 'Not done' check adds false lines to Toolsmith replies, and a finished reply ends with the out-of-domain line"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-612-toolsmith-reply-no-false-not-done]
  checks: [tests/unit/kernel/test_card612_not_done_toolsmith.py]
branch: feat/card-612-not-done-false-lines
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-599
  - CARD-604
  - CARD-571
  - CARD-596
---

# CARD-612 The CARD-599 'Not done' check adds false lines to Toolsmith replies, and a finished reply ends with the out-of-domain line

## Problem
In the CARD-607 live runs (2026-10-03, :8770, nemotron-3.5-lightning, 5 Ask Developer runs) Toolsmith saved every tool correctly, but:
- Run 2 ended with "Not done: Register tool with target agent tutor." although `register_native_tool` ran with `target_agent_id=tutor` and the attach proposal exists.
- Runs 3 and 5 ended with 5 lines such as "Not done: language hint none - not addressed.", "Not done: runtime hint none ...", "Not done: path/context ...", "Not done: packaging preference unspecified ...". These are empty fields of the Ask Developer message, not parts of the request.
- Run 4 ended with "You can use Ask Developer to add this." after a completed save.
Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003d\toolsmith-run-2..5-chat-desktop.png`.

## Cause
- The CARD-599 (b) checker (`agent_kernel.py` ~L1810, `reply_rules.py` `NOT_DONE_PREFIX`) reads the whole user message as a list of parts. The Ask Developer message (`src/application/tools/developer_mediation.py` ~L118-124) is a structured brief with `Language hint: none`, `Runtime hint: none`, `Packaging preference (note only ...)` lines, and the checker treats each as a requested part. It also does not see that a tool call (register with a target agent) already did the step, as CARD-604 fixed for remember/recall.
- The out-of-domain instruction in `src/application/agent_skills/allowed_tools.py` ~L218 ("end your reply with 'You can use Ask Developer to add this.'") reaches Toolsmith, and the model appends it to an in-domain reply.

## Change
- The checker gets only the request part of an Ask Developer brief (or the brief marks its metadata lines as notes the checker skips); fields that are `none`/unspecified are never parts.
- A step done by a tool call in the turn (successful `register_native_tool`, attach proposal created) is not reported Not done (same mechanism as CARD-604).
- The out-of-domain line is not part of Toolsmith's instructions (or the rule says to add it only when refusing a request).

## What dies
"Not done" lines for empty brief fields and for steps a tool already did; the Ask Developer tail on a finished Toolsmith reply.

## Proof
- Journey `card-612-toolsmith-reply-no-false-not-done`: 5 Ask Developer runs on nemotron; 0 "Not done" lines when the tool was saved with its target; no "You can use Ask Developer" line on a completed save.
- Checks: the checker given an Ask Developer brief with `none` fields and a turn with a successful register returns ""; a genuinely skipped part (e.g. "also write a test") still yields one line (negative).

## Plan and decisions
- Fix the input to the checker rather than suppress its output, so real skipped parts still show.

## Findings
- (from the CARD-607 live runs, 2026-10-03)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Toolsmith replies no longer end with "Not done" lines for things it did, or for empty fields of the Ask Developer request.
