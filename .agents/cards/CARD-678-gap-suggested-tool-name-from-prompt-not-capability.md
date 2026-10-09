---
id: CARD-678
title: "Capability gap suggests a tool name built from the prompt words, not the capability"
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
  - CARD-663
---

# CARD-678 Capability gap suggests a tool name built from the prompt words, not the capability

## Backlog
Found in the CARD-663/665 live check on 2026-10-09 (Spark nemotron, throwaway :8770). Not started; needs Jacob's build approval.

## Problem
In the live check the fax gap had capability "fax" but `suggested_tool_name` "manage_do_not_call_any", built from the first words of the user's message ("Do not call any tools ..."). Skill Studio shows this name as the draft tool name.

## Cause
`CapabilityDetector._suggest_tool_name(extracted, prompt_clean)` uses the prompt instead of the capability whenever the capability is 3 characters or fewer (`len(capability_text) > 3`), so "fax" or "sms" falls back to the first prompt words.

## Change (proposal)
Build the suggested name from the extracted capability first ("fax" -> `send_fax` or `fax_tool`), and use the prompt only when no capability was extracted.

## Proof
- Check (failing first): the fax and email admissions suggest names containing "fax" and "email", and nothing from the prompt's filler words.
