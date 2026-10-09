---
id: CARD-681
title: "Formulate sometimes calls an invented tool name (wiki_template_search)"
type: bug
status: Ready
priority: P3
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-665
  - CARD-676
---

# CARD-681 Formulate sometimes calls an invented tool name (wiki_template_search)

## Backlog
Found in the CARD-676 live check on 2026-10-09 (throwaway :8770, Spark :8006 nemotron-3.5-lightning only). Not started; needs Jacob's build approval.

## Problem
After CARD-674/676 a wiki job's Formulate step is sent every granted read tool and no real tool is refused. In 1 of 3 wiki jobs the model still called `wiki_template_search`, a tool that does not exist, right after it had called `wiki_template_list` successfully. The refusal was correct and helpful ("No tool with this name exists. Did you mean wiki_template_read or wiki_template_list?"), but it costs a round.

## Cause (to confirm)
Model behavior: it guesses a plausible name by analogy with `wiki_note_search`. The offered set and the CARD-665 tools block already list the real names.

## Change (proposal)
- Measure over more jobs first (1 in 3 here). If it repeats, consider a search parameter on `wiki_template_list` (filter by text) so the natural "search templates" call exists, rather than more prompt text.

## Proof
- Lean live: five wiki jobs whose Formulate steps call no invented tool names.
