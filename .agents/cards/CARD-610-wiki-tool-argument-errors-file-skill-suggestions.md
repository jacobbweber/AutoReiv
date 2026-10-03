---
id: CARD-610
title: "Nemotron passes unsupported arguments to wiki tools, and each refusal files a skill suggestion that needs approval"
type: bug
status: Ready
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-610-wiki-args-no-approval-noise]
  checks: [tests/unit/orchestration/test_card610_ace_skips_argument_errors.py]
branch: feat/card-610-wiki-args-no-approval-noise
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-523
  - CARD-562
  - CARD-589
  - CARD-605
  - CARD-607
  - CARD-110
---

# CARD-610 Nemotron passes unsupported arguments to wiki tools, and each refusal files a skill suggestion that needs approval

## Problem
In both job live checks on 2026-10-03 (:8770, nemotron-3.5-lightning, "search the wiki ... then summarize" run as a job), the Execute step called a wiki tool with an argument it does not accept, for example `wiki_note_list(limit=...)`. The tool correctly refused ("Unknown: limit. Accepted parameters: category, domain, topic, status, tag, author, pinned, priority. Nothing was run"). Jacob also reported `tag` being passed where it is not accepted. Each refusal then filed a `propose_skill` approval, "Append ACE insight to wiki SOP" (source `online-ace`), on the job's step session. The chat shows an Approve/Reject card and Recent Chats marks it "Needs approval" (CARD-493/608) for what is only tool-call noise. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003c\resumed-done-desktop.png`, `...\ui1003c\recent-chats-after-resume-desktop.png`, `...\ui1003b\job-after-resume-desktop.png` (the same pattern with `wiki_overview` `tool_not_offered`).

## Cause
- The model guesses parameter names (`limit`) the wiki tools never had; the tool schemas sent to it are the source of truth, so the guess is a model or prompt issue, not a missing parameter.
- Online ACE (`record_failed_turn_delta` in `src/application/orchestration/ace_online.py`, called from `agent_kernel.py`) treats any tool error in a skill turn as a lesson and drafts a `propose_skill` HITL approval, including argument refusals ("called with arguments it does not accept", CARD-562) and `tool_not_offered`. Those are already self-correcting: the refusal text tells the model the accepted parameters, and the next call usually succeeds.

## Change
- Online ACE skips tool errors that are argument refusals or `tool_not_offered` (or at most records them as a sidecar note, never an approval). Real tool failures still draft a suggestion.
- Check the wiki skill runbook (`skills/wiki/SKILL.md`) and wiki tool descriptions for wording that invites `limit` (or `tag` where it is not accepted); remove it. Do not add a `limit` parameter just to absorb the guess.

## What dies
"Append ACE insight to wiki SOP" approvals for argument mistakes the tool already corrected.

## Proof
- Journey `card-610-wiki-args-no-approval-noise`: 3 runs of the wiki-search-and-summarize job on nemotron; no `propose_skill` approval from `online-ace` for an argument refusal or `tool_not_offered`; the chat is not marked Needs approval.
- Checks: `record_failed_turn_delta` with an "arguments it does not accept" error or `tool_not_offered` drafts no approval; with a real tool failure it still drafts one (negative assertion).

## Plan and decisions
- Filter in online ACE rather than loosen the tool schemas: refusals already teach the model in-turn, and accepting unknown arguments would hide real mistakes.

## Findings
- (from docs/findings.md 2026-10-03, carded here)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-610\...`

## Release note
A wiki tool call with a wrong argument name no longer files a skill suggestion that needs your approval.
