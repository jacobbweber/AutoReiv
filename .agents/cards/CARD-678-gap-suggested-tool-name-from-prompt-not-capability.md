---
id: CARD-678
title: "Capability gap suggests a tool name built from the prompt words, not the capability"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/orchestration/test_card678_suggested_tool_name.py]
branch: fix/card-678-suggested-name-from-capability
log: {minutes: 20, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-663
---

# CARD-678 Capability gap suggests a tool name built from the prompt words, not the capability

## Backlog
Found in the CARD-663/665 live check on 2026-10-09 (Spark nemotron, throwaway :8770). Jacob approved the build on 2026-10-09.

## Problem
In the live check the fax gap had capability "fax" but `suggested_tool_name` "manage_do_not_call_any", built from the first words of the user's message ("Do not call any tools ..."). Skill Studio shows this name as the draft tool name.

## Cause
`CapabilityDetector._suggest_tool_name(extracted, prompt_clean)` uses the prompt instead of the capability whenever the capability is 3 characters or fewer (`len(capability_text) > 3`), so "fax" or "sms" falls back to the first prompt words.

## Change (proposal)
Build the suggested name from the extracted capability first ("fax" -> `send_fax` or `fax_tool`), and use the prompt only when no capability was extracted.

## Proof
- Check (failing first): the fax and email admissions suggest names containing "fax" and "email", and nothing from the prompt's filler words.

## Root cause
`_suggest_tool_name` used the capability only when it was longer than 3 characters (`len(capability_text) > 3`). "fax" and "sms" fell back to the first words of the prompt, so the live fax gap was named `manage_do_not_call_any`.

## Fix
The capability is used whenever it has at least 2 characters; the prompt is only a fallback when nothing was extracted. The live fax admission now suggests `manage_fax`.

## Checks
`tests/unit/orchestration/test_card678_suggested_tool_name.py` failed first (3 failed, including the exact live name `manage_do_not_call_any`) and passes now. The fax, email and SMS admissions give names containing "fax", "email" and "sms" with none of the prompt's filler words.
