---
id: CARD-604
title: "Multi-ask runs: nemotron skips memorize_fact in about 30-40% of runs, and the CARD-599 checker can mark a recall that ran as Not done"
status: In Review
created: 2026-10-02
branch: feat/card-604-605-memory-and-wiki-budget
related:
  - CARD-599
  - CARD-597
labels:
  - type:bug
  - area:kernel
  - area:memory
  - area:models
  - P2
needs_decision: none
milestone: M24
---

# [CARD-604] Multi-ask runs: nemotron skips memorize_fact in about 30-40% of runs, and the CARD-599 checker can mark a recall that ran as Not done

> **Status**: In Review (2026-10-03)
> **Labels**: `type:bug`, `area:kernel`, `area:memory`, `area:models`, `P2`

## Why

Found in the CARD-599/600 live checks (2026-10-02, throwaway :8770, Spark nemotron-3.5-lightning):

- **Skipped memorize.** When "remember X" is one ask among several, nemotron does not call `memorize_fact` in about 30-40% of runs. This happened on AutoReiv ("Remember that my favorite harbor is Bar Harbor, tell me this chat's session ID, list the wiki templates..., and search the wiki...") and on Toolsmith ts-02. Since CARD-599 the skip is named in a "Not done: Remember ..." line, but the fact is still not saved. Before the CARD-599 check, one run replied "noted ✓" with no memorize call.
- **Checker false positive.** In 1 of 5 ts-02 runs, the CARD-599 checker (v2, part by part) appended "Not done: Recall test token memory" although `recall_agent_memory` had run.

Results JSONs: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1002c\c599_autoreiv*.json`, `c599_ts02*.json`.

## Scope

1. **Reproduce:**
   - Run the AutoReiv 4-ask prompt and ts-02, 5 runs each on nemotron.
   - Count memorize asks that were done, named as Not done, or claimed with no tool call.
2. **Fix the memorize skip, cheapest first:**
   - a. Check the `memorize_fact` description and the "## Answering" rule. A request to remember something needs the tool call in the same turn.
   - b. If (a) is not enough: when the CARD-599 check finds a memory ask not done, give the model one tool step to do it, and only then append "Not done".
   - No model swaps.
3. **Fix the checker false positive:**
   - Make sure the checker sees each tool call that ran, with its name and short arguments, for every part.
   - Add the recorded ts-02 reply to the offline checker probe as a case.

## Out of scope

Model changes. Memory extraction (CARD-597).

## Acceptance criteria

- 5 runs of each prompt on nemotron: every memorize ask is either saved by `memorize_fact` or named as Not done, and no reply claims a save without the tool call.
- At least 8 of 10 runs save the fact.
- The checker writes no "Not done" for a part whose tool ran (10 runs, plus the offline probe).
- Full preflight is green.

## Change

Shared branch with CARD-605: `feat/card-604-605-memory-and-wiki-budget` (both change `agent_kernel.py`).

- Rule "## Answering" gains: "When asked to remember something, save it with memorize_fact in the same reply. Never say it is saved without that call." The `memorize_fact` description says the same.
- CARD-599 check:
  - The prompt now says remembering is done only by `memorize_fact`, and recalling only by `recall_agent_memory`.
  - `drop_false_not_done` removes a memory "Not done" line when the matching memory tool ran and succeeded.
- One retry step (Chat `stream_turn` only):
  - Trigger: the check names a "remember" part as Not done, and `memorize_fact` is offered.
  - The kernel saves the first reply, adds a one-off, unsaved "(AutoReiv check)" prompt, and gives the model one more step.
  - Afterwards the memory line is dropped if `memorize_fact` succeeded and kept otherwise. Other Not done lines stay, and the check is not run again.
- Tests: `tests/unit/kernel/test_card604_memory_asks.py` (7).

## Results

| Check | Result | Notes |
|---|---|---|
| Kernel suite | PASS | 227 passed |
| Full pytest | PASS | 2335 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2335, vitest 952, smoke 77 |
| Live AutoReiv 4-ask prompt (remember Bar Harbor, session ID, list templates, search weekly planning), 10 runs on two builds | PASS | memorize_fact 10/10; no Not done lines |
| Live Toolsmith ts-02 (6 asks), 5 runs | PASS | memorize_fact 5/5, recall 5/5. Not done lines only for "list the agents" (5/5; lookup_agents not offered) and "read README.md" (4/5; the reads failed). No memory false positives. |

Before (2026-10-02 runs in `ui1002c`): memorize_fact was skipped in about 30-40% of runs, and one run claimed a save with no tool call. Acceptance (at least 8 of 10 saved, no claim without the call, no false positive for a tool that ran) is met: 15/15 saved.

The retry step never triggered live, because memorize_fact was never skipped in these 15 runs. The unit tests cover it.

Borderline: in 2 ts-02 runs the reply listed the agents from its own instructions, and the checker still wrote "Not done: list the agents", because lookup_agents did not run. Left as is.

Live env: throwaway :8770 from a temporary merge of the two CARD branches (deleted after), Spark nemotron-3.5-lightning only. Results: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003\c604_autoreiv.json`, `c604_autoreiv2.json`, `c604_ts02.json`.

## Release note

When you ask an agent to remember something in a multi-part Chat request, it now saves the fact with memorize_fact. If it skipped that, it gets one more step to save it before the reply says Not done.
