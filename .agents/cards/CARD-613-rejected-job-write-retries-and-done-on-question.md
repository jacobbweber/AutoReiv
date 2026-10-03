---
id: CARD-613
title: "After a job's write card is rejected the model retries 4-5 times and asks why; the job is then marked done though the reply is a question"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-613-rejected-write-ends-cleanly]
  checks: [tests/unit/kernel/test_card613_rejection_is_final.py]
branch: feat/card-612-613-614-reply-honesty
log: {minutes: 170, qa_runs: 4, findings: 4}
created: 2026-10-03
completed: 2026-10-03
related:
  - CARD-600
  - CARD-572
  - CARD-490
  - CARD-610
---

# CARD-613 After a job's write card is rejected the model retries 4-5 times and asks why; the job is then marked done though the reply is a question

## Problem
In the CARD-610 live runs (2026-10-03, :8770, nemotron-3.5-lightning, "search the wiki for gardening, then a 600-word summary" run as a job), the Execute step chose to call `wiki_note_create`. Rejecting the approval card made the step call `wiki_note_create` again: 5 rejections in run 2 (10 calls), 4 in run 3 (8 calls). Each run ended with `ask_clarification`: "The wiki_note_create tool is being rejected without a clear error message ... Could you check the session approval mode ...?". The job was then marked `done`, although the reply is a question and the summary was never written. Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003d\wiki-job-2-chat-desktop.png`.

Separately, rejecting through `POST /api/approvals/{id}/decision` (no UI) returned `resume_chat: true, resumed: false`, and job 1 stayed `waiting_approval`.

## Cause (to confirm)
- The tool result the model sees after a rejection does not say plainly that the operator declined this action and it must not be retried; the model reads it as an unexplained failure.
- The job's done rule treats a turn that ends in `ask_clarification` (CARD-600 item 5: the question is the reply) as the step finishing.

## Change
- The rejection result says: "Jacob declined <tool>. Do not call it again in this reply; finish the request without it, or say what you could not do." The kernel refuses a repeat call of the same tool with the same arguments in the same turn after a rejection.
- A job step that ends with a clarification question is `waiting` (needs Jacob's answer), not `done`; the job strip says so.
- Check the API-only rejection path resumes the job (or leaves it clearly stopped with Resume).

### Built (2026-10-03)
- `repeat_guard.py`: rejection result text "Rejected. Tool did not run. The operator rejected this X call. Do not call X again for this request: finish without it (give the result in your reply instead) and say plainly what was not done."; `rejected_tool_names(history)` (since the last user message); `RepeatGuard` refuses a repeat with `tool_rejected:` and no new card. The kernel (both paths) also drops rejected tools from the offered set. `hitl.py` writes the same text.
- A step that ends with `ask_clarification` is a question: the orchestrator's `wait_for_answer` sets the phase queued with reason "waiting for your answer", the strip shows it (no Resume), and Jacob's next chat message is sent as the answer and the step continues.
- `kill_resume.job_left_parked`: a job parked on an approval that was decided outside the chat (API) with nothing pending shows "Job stopped" + Resume (verify-gate parks excluded).
- Tests: `tests/unit/kernel/test_card613_rejection_is_final.py` (10), `tests/unit/frontend/card_613_waiting_answer.test.js`.

## What dies
Retry loops after a rejection; jobs marked done on a question.

## Proof
- Journey `card-613-rejected-write-ends-cleanly`: 3 runs of the wiki job with the write card rejected; at most 1 call of the rejected tool after the rejection, the reply gives the summary or names what was not done, and a step ending in a question is not marked done.
- Checks: the rejection result text; a repeat of a rejected call in the same turn is refused; a step whose last tool is `ask_clarification` does not set the job done (negative: a normal final reply still does).

## Plan and decisions
- Keep rejection final for the turn; do not auto-resume a different tool on Jacob's behalf.

## Findings
- (from the CARD-610 live runs, 2026-10-03)
- A job is still marked done when the final reply asks a plain-text question (not `ask_clarification`); treating "?" as a question was rejected as too heuristic. Open decision.
- Execute was sometimes not offered `wiki_note_create` (tool narrowing; empty-wiki/tomatoes variant), so the model said "tool not available" instead of getting a card.
- After an API rejection, the strip shows STOPPED + Resume but the job card in the chat body still says "Execute RUNNING..." and the old "waiting for operator approval" message stays until Resume.
- The model sometimes quotes the rejection text back ("per the runbook directive ..."); harmless.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-613 wiki job run 2, UI reject | desktop | Pass | 1 rejection, 0 repeats; honest reply but summary not shown -> rejection text now asks for the result in the reply (da38c6bf). `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-2-ui-card-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-2-ui-end-desktop.png` |
| card-613 wiki job run 3, UI reject (da38c6bf) | desktop | Pass | 1 rejection, 0 repeats, summary in the reply, "What was not done" names the note; job done. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-3-ui-card-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-3-ui-end-desktop.png` |
| card-613 wiki job run 4, API reject | desktop | Pass | after reload: "Job stopped" + Resume; Resume continued, no new card, 1 call of the rejected tool, job done; reply ended with an Ask Developer line (finding). `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-4-api-card-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-4-api-stopped-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-4-api-end-desktop.png` |
| card-613 wiki job run 1, empty wiki | desktop | Pass (no card) | nothing to save, honest "no content"; ended with Ask Developer line. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\wiki-job-1-ui-end-desktop.png` |

## Release note
When you reject an action in a job, the agent stops asking for it again and finishes without it, and a job that ends with a question waits for your answer instead of showing Done.
