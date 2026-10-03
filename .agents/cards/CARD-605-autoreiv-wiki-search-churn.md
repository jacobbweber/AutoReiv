---
id: CARD-605
title: "AutoReiv makes about 21 wiki search/list calls for one simple search or a missing note"
status: In Review
created: 2026-10-02
branch: feat/card-604-605-memory-and-wiki-budget
related:
  - CARD-551
  - CARD-461
labels:
  - type:bug
  - area:kernel
  - area:wiki
  - P2
needs_decision: none
milestone: M24
---

# [CARD-605] AutoReiv makes about 21 wiki search/list calls for one simple search or a missing note

> **Status**: In Review (2026-10-03)
> **Labels**: `type:bug`, `area:kernel`, `area:wiki`, `P2`

## Why

Found in the CARD-599/600 live checks (2026-10-02, :8770, nemotron-3.5-lightning). AutoReiv sometimes made up to about 21 `wiki_note_search` / `wiki_note_list` calls in one turn. This happened for "search the wiki for notes about weekly planning" (the wiki has no such notes) and when it was asked to read the missing note `00_Inbox/zz-missing-note.md`.

The CARD-551 repeat guard does not catch this, because each call has slightly different arguments. Each extra call costs local model time.

## Scope

1. **Reproduce:**
   - Run both prompts 5 times each on nemotron.
   - Count search/list calls per turn.
2. **Fix, cheapest first:**
   - a. A rule in AutoReiv's instructions or the wiki tool descriptions: after 2-3 searches with no hit, say nothing was found and suggest a next step.
   - b. If (a) is not enough: a per-turn budget for wiki search/list calls. Past the budget, the tool result tells the model to answer with what it has.
   - No model swaps.

## Out of scope

Search quality. Model changes.

## Acceptance criteria

- 10 runs on nemotron: no more than 5 wiki search/list calls in any turn.
- The reply says plainly that nothing matched, or that the note does not exist.
- Full preflight is green.

## Change

Shared branch with CARD-604: `feat/card-604-605-memory-and-wiki-budget`.

- New `src/application/kernel/wiki_budget.py` (`WikiLookupBudget`): at most 4 `wiki_note_search` / `wiki_note_list` calls per reply, in both `run_turn` and `stream_turn`.
  - Repeats (CARD-551 reuse) and calls with bad arguments count against it.
  - Past the budget the call gets "Not run: you already looked in the wiki 4 times in this reply...". This is a success result, so it never adds a CARD-600 failed note.
  - The two look-up tools are also no longer offered for the rest of that reply.
- The search and list descriptions now say: "If two or three look-ups find nothing, stop and say plainly that no matching note was found."
- Tests: `tests/unit/kernel/test_card605_wiki_lookup_budget.py` (7).

## Results

| Check | Result | Notes |
|---|---|---|
| Kernel suite | PASS | 227 passed |
| Full pytest | PASS | 2335 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2335, vitest 952, smoke 77 |
| Live before (qa), "Search the wiki for notes about weekly planning." x3 | - | 10, 5, 8 look-ups |
| Live before (qa), "Read the note 00_Inbox/zz-missing-note.md..." x3 | - | 3, 2, 2 look-ups |
| Live after (final build), simple search x5 | PASS | 4 ran + 1 refused in every run (5 calls max); all 5 replies say no weekly planning notes were found |
| Live after (final build), missing note x5 | PASS | 1, 1, 4, 2, 2 look-ups; all 5 say the note does not exist |
| Live after, AutoReiv 4-ask prompt x5 | PASS | 4 ran + at most 1 refused (5 calls max) |

An earlier build did not count repeats, and one 4-ask run made 6 calls (4 counted, 1 repeat, 1 refused). Fixed in `d2f3b84b`, which made repeats and failed calls count and stopped offering the tools after the budget. The final-build numbers above come after that fix.

Live env: throwaway :8770, Spark nemotron-3.5-lightning only. Results: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003\c605_*_before.json`, `c605_*_after.json`, `c605_*_after2.json`.

## Found while testing

- When the budget refuses a call, the model sometimes mentions it in the reply (one run showed "Blocked (4 prior wiki look-ups in this reply)" in a table).
- AutoReiv still sometimes calls the wiki tools with arguments they do not accept (`tag` on search, `limit` on list).

## Release note

An agent now makes at most 4 wiki searches or lists per reply, then answers with what it found, and says plainly when nothing matched.
