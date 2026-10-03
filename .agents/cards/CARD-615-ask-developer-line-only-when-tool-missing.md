---
id: CARD-615
title: "Job replies that could not finish a step end with the Ask Developer line even when the tool exists; add that line in code, not by prompt"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-615-no-ask-developer-tail-when-tool-exists]
  checks: [tests/unit/kernel/test_card615_ask_developer_line.py]
branch: feat/card-615-ask-developer-line-only-when-tool-missing
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-612
  - CARD-596
  - CARD-613
---

# CARD-615 Job replies that could not finish a step end with the Ask Developer line even when the tool exists; add that line in code, not by prompt

## Problem
In the CARD-613 live runs (2026-10-03, :8770, nemotron-3.5-lightning) AutoReiv ended 3 of 4 wiki job replies with "You can use Ask Developer to add ..." although the tool exists (`wiki_note_create`): run 1 (empty wiki, nothing to save), run 2 and run 4 (the write card was rejected). CARD-612 changed the prompt rule to "Only a reply that turns the request down ends with that line"; nemotron does not follow it. The line sends Jacob to build a tool he already has.
Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-1-ui-end-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-2-ui-end-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-4-api-end-desktop.png`.

## Cause
`src/application/agent_skills/allowed_tools.py` `domain_line()` puts the instruction "end your reply with 'You can use Ask Developer to add this.'" in every non-Toolsmith system prompt (`agent_kernel.py` "## Your domain"). The model copies the line into any reply that reports something not done, whatever the reason.

## Change
- Take the line out of the prompt: `domain_line()` keeps "say plainly which agent to open in Chat" / "say plainly that no agent covers it", and no longer tells the model to write the Ask Developer sentence.
- The kernel adds the sentence itself, once, at the end of the reply, only when a tool is truly missing in this turn: a call refused as an unknown tool or a tool the agent does not have (not `tool_not_offered` for a tool the agent owns, not a rejection, not an argument error), or the parts check / router marks the request out of domain. The Ask Developer button stays where it is.
- If the model still writes the sentence on its own, it is dropped from the saved reply when a tool of the agent ran this turn (a finished stream gets the cleaned text with the existing final-content event; check whether the UI already replaces the bubble on it before adding anything).

## What dies
The prompt instruction to end with the Ask Developer line; the line on replies about rejected, empty or partly done work.

## Proof
- Journey `card-615-no-ask-developer-tail-when-tool-exists`: 3 wiki job runs on nemotron with the write card rejected and 1 with an empty wiki: no Ask Developer line. 1 run asking AutoReiv for something no agent covers (e.g. "send a fax"): the line is there once.
- Checks: the system prompt has no Ask Developer sentence; the line is added for an unknown-tool refusal and for an out-of-domain request; it is not added (and a model-written one is dropped) after a rejection or a successful tool call (negative).

## Plan and decisions
- Engineering call: deterministic over prompt. Keep it to one helper next to `drop_false_not_done` in `reply_rules.py`.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Agents add "You can use Ask Developer to add this." only when a tool is really missing, not after you reject an action or when there was simply nothing to do.
