---
id: CARD-674
title: "Formulate (plan) step is still sent write tools that have no declared risk"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-08
completed:
related:
  - CARD-554
  - CARD-665
---

# CARD-674 Formulate (plan) step is still sent write tools that have no declared risk

## Backlog
Found while building CARD-665 on 2026-10-08. Not started; needs Jacob's build approval.

## Problem
A job's Formulate step should only plan ("do not call tools that change anything", CARD-554). On the shipped AutoReiv profile, a wiki job's Formulate call ("Summarize my gardening notes into a new wiki note using the summary template") is still sent `wiki_template_create`, `wiki_template_update` and `wiki_note_archive`. Those tools change the vault. The model can call them while planning, and CARD-665's tools block lists them as callable because they really are sent.

## Cause
`phase_roles.planning_phase_block_reason` blocks only `handoff_to_agent`, tools in `hitl_engine.DEFAULT_HIGH_RISK_TOOLS`, and tools whose declared risk is high or critical. No registered tool declares a risk: `ScopedToolRegistry.get_tool_risk` is empty for all 37 tools AutoReiv is granted, and the capability index seeds every tool as `RiskLevel.LOW`. Writes outside the high-risk list (template create/update, note archive, and probably others such as `promote_artifact_to_wiki` or `memorize_fact`) pass as read-only.

## Change (proposal)
Give tools a declared risk tier at registration (read_only / write / network / destructive, the CARD-539 D11 field that exists but is unused). Then plan only the read-only ones in a planning phase, and fail closed for an undeclared tool in that phase. This is a structural fix, not a longer name list.

## Proof
- Check: every registered platform tool declares a risk, and a test fails on an undeclared one.
- Check: a Formulate call for the AutoReiv wiki job is sent no write or destructive tool.
- Lean live: one wiki job Formulate step whose offered set (CARD-665 tools block) holds only read tools.
