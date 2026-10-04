---
id: CARD-616
title: "A job step whose last reply asks a plain-text question is marked Done instead of waiting for the answer"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-616-job-waits-on-plain-question]
  checks: [tests/unit/kernel/test_card616_plain_question_waits.py]
branch: feat/card-616-618-question-wait-and-distill-limit
log: {minutes: 140, qa_runs: 8, findings: 3}
created: 2026-10-03
completed: 2026-10-03
related:
  - CARD-613
  - CARD-600
---

# CARD-616 A job step whose last reply asks a plain-text question is marked Done instead of waiting for the answer

## Problem
CARD-613 made a job step that ends with `ask_clarification` wait for Jacob's answer. In its live runs (2026-10-03, nemotron) a wiki job variant ("tomatoes") ended Execute with a question written as plain text and no `ask_clarification` call; the job was marked Done, the strip said Job done and the question was left hanging.

## Cause
`src/application/orchestration/job_phase_orchestrator.py` / `src/web/routers/chat.py` `_stream_turn_bound` treat a step as a question only when the turn ended through `ask_clarification` (TURN_END `react={"clarification": True}`). A final reply that asks in plain text ends the step as done.

## Change
Pick one (engineering call at build time; the simpler that holds on nemotron wins):
- Phase prompts already ask for `ask_clarification`; add a no-tools check on the same model only for a job step whose final reply ends with a question line (last non-empty line ends with "?"), asking "does this reply need the user's answer before the work can continue? yes/no". Yes -> same path as `ask_clarification` (`wait_for_answer`).
- Or: the step's final reply ending with a question line is enough to wait, with the strip offering "Mark done" as well as answering.
CARD-613 rejected a bare "?" rule as too heuristic, so the first option is preferred.

### Built (2026-10-03)
- `src/application/orchestration/plain_question.py`: `ends_with_question` (last non-empty line ends with "?") and `reply_needs_answer`: one yes/no call on the step's own model (`kernel._resolve_model(profile)`), no tools, thinking off, 4 worked examples (two real questions, two closing offers). Any failure keeps the step done.
- `chat.py` `_stream_turn_bound`: a step that would end done is checked first; yes -> the existing CARD-613 `wait_for_answer` path (strip "Job waiting for answer", the next chat message answers it).
- `chat.py` answer continuation: when the answered step finishes and the next step asks, the chat now gets the finished reply and the new question and keeps waiting (before, the question never reached the chat).
- `openai_adapter.py`: `think=False` on the vLLM provider sends `chat_template_kwargs.enable_thinking=false` (only this check sets think=False).

## What dies
Jobs marked Done while the last reply asks Jacob something.

## Proof
- Journey `card-616-job-waits-on-plain-question`: a job prompt that makes nemotron ask in plain text (the tomatoes variant from CARD-613); the strip shows waiting for your answer, no Done; answering continues the same step.
- Checks: a final reply ending with a real question waits; a reply ending with a rhetorical/closing "Anything else?" after finished work is done (negative); `ask_clarification` path unchanged.

## Plan and decisions
- Engineering call: the card's preferred option (yes/no check only for a last line ending in '?'), routed to CARD-613's wait path; no 'Mark done' button.

## Findings
- (from the CARD-613 live runs, 2026-10-03; docs/findings.md)
- 2026-10-03: with thinking on, nemotron spent the whole budget reasoning (600 tokens, empty answer) and read closing offers as questions; thinking off without examples also read every offer as a question; thinking off + 4 worked examples was 21/21 on 7 cases x3 through the real vLLM adapter.
- 2026-10-03: a later step does not see Jacob's answer, so Execute asked the vegetables question again; carded as CARD-619.
- 2026-10-03: a waiting job shows a STOPPED badge on the strip; carded as CARD-620.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-616 run 1 (pre-fix 0c8e639f): vegetable job, plain question | desktop | PARTIAL | Formulate's plain question waited (no ask_clarification); after the answer Execute asked again and its question never reached the chat. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-1-first-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-1-answered-desktop.png` |
| card-616 run 1b (0c8e639f): same job | desktop | PASS | Waited at Formulate; after the answer Execute's question shown and waited; second answer -> Job done with the note. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-1b-first-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-1b-answered-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-1b-answered2-desktop.png` |
| card-616 run 2 / 6: gardening summary job | desktop | PASS | No question -> Job done. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-2-first-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-6-first-desktop.png` |
| card-616 run 4 / 7: summary ending "anything else?" | desktop | PASS | Courtesy question -> Job done (check said no). `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-4-first-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-7-first-desktop.png` |
| card-616 run 5 (final ad055475): vegetable job | desktop | PASS | Same as 1b on the final check (no thinking + examples). `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-5-first-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-5-answered-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-5-answered2-desktop.png` |

## Release note
A job step that ends by asking you something waits for your answer instead of showing Done.
