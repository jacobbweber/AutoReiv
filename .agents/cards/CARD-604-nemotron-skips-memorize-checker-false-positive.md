---
id: CARD-604
title: "Multi-ask runs: nemotron skips memorize_fact in about 30-40% of runs, and the CARD-599 checker can mark a recall that ran as Not done"
status: Ready
created: 2026-10-02
branch: qa
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

> **Status**: Ready (filed 2026-10-02)
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
