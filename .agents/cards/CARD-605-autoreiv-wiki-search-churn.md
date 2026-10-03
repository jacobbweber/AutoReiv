---
id: CARD-605
title: "AutoReiv makes about 21 wiki search/list calls for one simple search or a missing note"
status: Ready
created: 2026-10-02
branch: qa
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

> **Status**: Ready (filed 2026-10-02)
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
