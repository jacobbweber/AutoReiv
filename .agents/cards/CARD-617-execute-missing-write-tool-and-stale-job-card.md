---
id: CARD-617
title: "Job Execute step is sometimes not given wiki_note_create; after an API reject the job card body still shows Execute RUNNING"
type: bug
status: In Review
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-617-execute-has-write-tool-and-card-matches-strip]
  checks: [tests/unit/kernel/test_card617_execute_tools.py, tests/unit/frontend/card_617_job_card_stopped.test.js]
branch: feat/card-615-617-ask-developer-line-and-job-tools
log: {minutes: 120, qa_runs: 3, findings: 1}
created: 2026-10-03
related:
  - CARD-613
  - CARD-607
  - CARD-490
---

# CARD-617 Job Execute step is sometimes not given wiki_note_create; after an API reject the job card body still shows Execute RUNNING

## Problem
From the CARD-613 live runs (2026-10-03, :8770, nemotron):
1. In a wiki job ("tomatoes" variant, and the empty-wiki run) the Execute step was not offered `wiki_note_create`: the model's call came back `tool_not_offered` and the reply said the tool was not available, so no write card appeared. AutoReiv has the tool; the plan named it.
2. After a write card was rejected through the API (`POST /api/approvals/<id>/decision`), reload shows the strip "Job stopped ... STOPPED Resume" (correct, CARD-613), but the job card in the chat body still says "Execute RUNNING..." and the old message "Job ... is waiting for operator approval during Execute. Approve or reject above" stays until Resume.
Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-4-api-stopped-desktop.png`.

## Cause (to confirm)
1. `src/application/kernel/agent_kernel.py` `_resolve_active_tools()` narrows the tools per turn (skill/relevance); for a job phase the step text may not pull in the wiki write tool. Log the offered set for the failing prompt first.
2. `src/web/static/modules/studios/chat/job_chrome.js` renders the phase list from the phase status (`running`) and does not use the journey's `stopped` flag that the strip uses; the parked message is written by `src/web/routers/chat.py` (around L1273) and never replaced.

## Change
1. A job step is offered every tool its plan step names that the agent has (or the narrowing never drops the agent's own write tools in a job phase); keep the refusal for tools the agent does not have.
2. The job card shows the same state as the strip: a stopped job's running phase shows "Stopped" (Resume lives on the strip); the parked "waiting for operator approval" line is not shown once nothing is pending.

### Built (2026-10-03)
- Cause confirmed: AutoReiv ticks `wiki-knowledge` (search/read/list/graph) and gets `wiki_note_create` from `wiki-inbox`. The job resolver matched `skill.wiki-knowledge` + `tool.wiki_note_create`, but the kernel's phase-skill filter in `_resolve_active_tools` kept only wiki-knowledge's tools, so create was dropped (the gate did not apply that filter, hence NOT_OFFERED). Fix: the filter also keeps tools the job matched by name. Tools the agent lacks are still refused.
- Job card: `buildInlineJobChromeFromJourney` marks the open phase `stopped` (or `waiting`) from the journey, not running; `job_chrome.js` shows "Stopped" / "Waiting for your answer" in amber.
- Park note: the hitl decision route rewrites the origin chat's "paused for approval" note to "... the card was rejected/approved." (`chat_job_binding.settle_park_note`).
- `index.html` -> `app.js?v=2.0.104`.

## What dies
"Tool not available" replies for tools the agent has; a job card saying RUNNING under a STOPPED strip.

## Proof
- Journey `card-617-execute-has-write-tool-and-card-matches-strip`: the tomatoes and gardening wiki jobs on nemotron get a write card (3 runs); an API reject + reload shows Stopped in both strip and card.
- Checks: offered tools for a job step that names `wiki_note_create` include it; a tool the agent lacks is still refused (negative); card render with `stopped: true` shows Stopped.

## Plan and decisions

## Findings
- (from the CARD-613 live runs, 2026-10-03; docs/findings.md)
- 2026-10-03: root cause was the ticked skill (wiki-knowledge) vs the skill that owns the write tool (wiki-inbox), plus the phase-skill filter; see Built.
- Behaviour change: a stopped job's open step now shows "Stopped" (CARD-490 showed Pending); decided park notes are rewritten in past tense.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-617 run 1: tomatoes job (failed before), nemotron | desktop | PASS | Execute called `wiki_note_create`, card raised, no NOT_OFFERED. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003g\run-1-card-desktop.png` |
| card-617 run 2: gardening job, API reject + reload | desktop | PASS | Strip "Job stopped ... STOPPED Resume"; card body "Execute STOPPED"; note "paused for approval during Execute; the card was rejected." `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003g\run-2-card-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003g\run-2-api-stopped-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003g\run-2-end-desktop.png` |
| card-617 run 5: gardening job, UI reject | desktop | PASS | Card raised for `wiki_note_create`, 1 rejection, no retry, job done. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003g\run-5-card-desktop.png` |

## Release note
Job steps get the tools their plan needs, and the job card in the chat matches the job strip after a stop.
