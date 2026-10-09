---
id: CARD-663
title: "Capability-gap detector misses some phrasings"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/orchestration/test_card663_missing_tool_phrasings.py]
branch: feat/card-663-gap-phrasings
log: {minutes: 45, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-08
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-661
  - CARD-662
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-663 Capability-gap detector misses some phrasings

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Problem
When an agent says it lacks a tool using some wordings (for example "I do not have a direct email-sending tool"), the capability-gap detector does not file a gap. Those gaps are then missing from Agent Studio / Skill Studio even though the reply told the operator the capability is missing. Logged from the Oct 5 uncarded findings (findings list also has the 2026-10-03 CARD-615 note).

## Cause
`CapabilityDetector` (and related reply rules) only match some phrasings. After CARD-615, reply rules gained their own "lacks tool" check for the Ask Developer line, but the detector that files gaps was left unchanged.

## Change
Widen the detector (or share one matcher with reply rules) so the known missed phrasings file a gap the same way the clearer ones do. Keep false positives low.

## What dies
Silent misses where the model admits a missing tool but no gap row is created.

## Proof
- Checks (failing first): each known missed phrasing from the findings produces a gap; a reply that does not admit a missing tool still does not.
- Live or journey only if the unit bar is not enough.

## Plan and decisions
Jacob approved the build on 2026-10-08. Prefer one shared matcher used by both the detector and the Ask Developer line so they cannot drift again.

## Root cause
Two separate matchers. `CapabilityDetector.detect` (files the gap) used a short list of fixed phrases ("I don't have the tools to", "I cannot directly", ...). CARD-615 gave `reply_rules` its own `_LACKS_TOOL` regex for the Ask Developer line. A reply such as "I do not have a direct email-sending tool" got the Ask Developer line but no gap row. "There is no fax tool", "I lack a tool for ..." and "The PDF export tool isn't available" got neither.

## Decisions
- New shared matcher `src/domain/capabilities/missing_tool.py` (`find_missing_tool`, `admits_missing_tool`, `names_own_tool`). It works sentence by sentence on the structure, not a phrase list. A gap is one of these:
  - a negated possession or reach verb (do not have / lack / cannot access, use or find) near a tool word (tool, capability, ability, integration, function, permission);
  - "there is no X tool" or "no tool is available to ...";
  - "X tool isn't available";
  - "cannot directly ..." or "... without a tool".
- Skipped: questions, conditionals (if/when/unless), sentences about the user ("you don't have"), "no tools were needed", "tool calls/output".
- The capability is taken from the words after to/for/that, or from the words in front of "tool" minus filler such as "direct", "built-in" or "any" (so "email-sending tool" gives "email sending"). If neither gives anything, it is the user prompt.
- `CapabilityDetector.detect(..., own_tools=())` uses the shared matcher. It files no gap when the admitting sentence names one of the agent's own tools, which is the same rule the Ask Developer line already used. Both kernel call sites (plain and streamed) pass `_own_tool_names(agent)`.
- `reply_rules._gap_sentence` uses the shared matcher, and `_LACKS_TOOL` is gone, so the line and the gap cannot drift again.

## Results
- New checks: `tests/unit/orchestration/test_card663_missing_tool_phrasings.py`. At the test commit the file failed at collection: the shared matcher did not exist, and the old detector filed no gap for the 9 missed wordings. After the fix all pass: 9 missed wordings, 3 still-caught ones, 13 replies that must not file a gap, the own-tool case, and an AST check that both kernel calls pass `own_tools`.
- Existing detector, CARD-615 and CARD-612 tests plus `tests/unit/architecture`: 71 passed on Jarvis. `ruff check src tests` is clean.

## Live check (2026-10-09, Spark nemotron-3.5-lightning, throwaway :8770 at 72e97b99)
Spark held only nemotron (gateway /v1/models: loaded=true for nemotron only). Every agent and the default on the throwaway serve were vllm/nemotron-3.5-lightning. The serve showed matches_index=True and health 200. AutoReiv in plain chat:
- "I do not have a direct email-sending tool in my skill set." filed a gap: capability "email sending", context_summary = the reply (so CARD-664 works live too), and the Ask Developer line was added. PASS.
- "I could not send the fax: there is no fax tool." filed a gap: capability "fax", with the Ask Developer line. PASS.
- "I do not have the tool wiki_note_create available." (AutoReiv's own tool) filed no gap and got no Ask Developer line. PASS.
- Natural asks ("Please fax my gardening notes to 555-0100.", "Email my gardening notes to bob@example.com right now.") got "No agent covers ..." replies. They carry the Ask Developer line but file no gap, because the reply names no tool. Filed as CARD-677.
- The fax gap's suggested_tool_name was `manage_do_not_call_any`, taken from the prompt words and not from the capability. Filed as CARD-678.
