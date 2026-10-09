---
id: CARD-681
title: "Formulate sometimes calls an invented tool name (wiki_template_search)"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/kernel/test_card681_invented_tool_name.py]
branch: fix/card-681
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-665
  - CARD-676
---

# CARD-681 Formulate sometimes calls an invented tool name (wiki_template_search)

## Backlog
Found in the CARD-676 live check on 2026-10-09 (throwaway :8770, Spark :8006 nemotron-3.5-lightning only). Jacob approved the build on 2026-10-09.

## Problem
After CARD-674/676 a wiki job's Formulate step is sent every granted read tool and no real tool is refused. In 1 of 3 wiki jobs the model still called `wiki_template_search`, a tool that does not exist, right after it had called `wiki_template_list` successfully. The refusal was correct and helpful ("No tool with this name exists. Did you mean wiki_template_read or wiki_template_list?"), but it costs a round.

## Cause (to confirm)
Model behavior: it guesses a plausible name by analogy with `wiki_note_search`. The offered set and the CARD-665 tools block already list the real names.

## Change (proposal)
- Measure over more jobs first (1 in 3 here). If it repeats, consider a search parameter on `wiki_template_list` (filter by text) so the natural "search templates" call exists, rather than more prompt text.

## Proof
- Lean live: five wiki jobs whose Formulate steps call no invented tool names.

## Root cause
A call to a tool name that does not exist (for example `wiki_template_search`, guessed by analogy with `wiki_note_search`) was refused with `NO_SUCH_TOOL` ("No tool with this name exists"). That wording and the refused name made the reply look like a missing capability: the capability detector filed a gap and the CARD-615 Ask Developer line was added when the model then said it had no such tool.

## Fix
- `tool_not_offered_error`: when the name is not a real tool and has close real names (`difflib`, cutoff 0.6, up to 3), the refusal says "No tool has this exact name; it looks like a mistyped or made-up name, not a missing capability. Did you mean X or Y? Call one of those instead." (`NEAR_MISS_TOOL_NAME`). A name with no close match (for example `send_fax`) keeps the `NO_SUCH_TOOL` wording and the CARD-615 behavior.
- `reply_rules.near_miss_tool_names()` / `near_miss_mentions()` read this turn's refusals. The near-miss names (and their spelled-out forms, such as "template search") count as the agent's own tools for the capability detector (`run_turn` and `stream_turn`) and for the Ask Developer line, so a slip is neither a gap nor an Ask Developer prompt.

## Checks
`tests/unit/kernel/test_card681_invented_tool_name.py` failed first (it could not import the new refusal constant; on the box the give-up case also added an Ask Developer line) and passes now (8 tests): close names are listed; `send_fax` stays a missing tool; an end-to-end turn that calls `wiki_template_search` recovers with `wiki_template_list`; giving up by exact name or in plain words files no gap and adds no Ask Developer line; a truly missing tool still gets the line.

Live on Jarvis, 2026-10-09 (throwaway :8772, own data folder, Spark :8006 nemotron-3.5-lightning only):
- Three wiki jobs plus one chat called no invented names (0 refused Formulate calls).
- A chat that insisted on `wiki_template_search`: refused with "Did you mean wiki_template_read or wiki_template_create or wiki_template_list? Call one of those instead.", the next call was `wiki_template_list`, the answer listed the templates, no Ask Developer line, and no gap for that session. The only gap on the serve came from an unrelated Formulate wording false positive, filed as CARD-684.
