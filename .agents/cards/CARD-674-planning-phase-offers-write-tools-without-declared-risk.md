---
id: CARD-674
title: "Formulate (plan) step is still sent write tools that have no declared risk"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/orchestration/test_card674_tool_read_write_labels.py]
branch: fix/card-674-read-write-labels
log: {minutes: 60, qa_runs: 1, findings: 0}
created: 2026-10-08
completed: 2026-10-09
related:
  - CARD-554
  - CARD-665
---

# CARD-674 Formulate (plan) step is still sent write tools that have no declared risk

## Backlog
Found while building CARD-665 on 2026-10-08. Jacob approved the build on 2026-10-09.

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

## Root cause
The plan-only rule (`phase_roles.planning_phase_block_reason`) was a block list: handoff, the HITL high-risk names, and tools with a declared high or critical risk. No platform tool declares a risk, so every other write passed as if it were a read. On the shipped AutoReiv profile a wiki job's Formulate call was sent `wiki_template_create`, `wiki_template_update` and `wiki_note_archive`.

## Fix
- `src/application/kernel/tool_access.py` labels every platform tool READ or WRITE (62 read, 50 write), with `tool_access(name, declared_risk)`. A risk declared at registration wins (`read_only` is read, anything else is write), so an MCP or runtime-built tool that says it is read-only can plan.
- Planning is now an allow list: `planning_phase_block_reason` lets only READ tools through. Handoff, WRITE tools and unlabeled tools (fail closed) are not sent to a Formulate step and the gate refuses them there. The same function drives the kernel's offered set, the gate and the CARD-665 tools block, so they agree.
- The label is separate from the registration `risk` field, which drives per-call confirmation, so labeling a tool WRITE adds no approval card in chat.
- A non-string risk (for example from a test double) counts as undeclared.

## Checks
`tests/unit/orchestration/test_card674_tool_read_write_labels.py` failed first (no `tool_access` module) and passes now (29 tests): every platform tool the real app registers has a label and no label is stale; read and write never overlap; the three writes seen live, plus other writes and handoff, are not used while planning; planner reads are; an unlabeled tool is not; a declared `read_only` risk counts as read; the gate blocks `wiki_template_create` in Formulate and allows `wiki_note_search`; the shipped AutoReiv Formulate step is sent read tools only.

Live on Jarvis, 2026-10-09: throwaway :8770 from the worktree, fresh data folder, Spark :8006 nemotron-3.5-lightning only. Wiki job "Summarize my gardening notes into a new wiki note using the summary template" (two seeded gardening notes). The Formulate step was sent only: ask_clarification, get_session_info, read_document_file, recall_agent_memory, wiki_note_list, wiki_note_read, wiki_note_search, wiki_template_list, wiki_template_read. It made no tool calls and no refused calls; Execute then read both notes and the templates and created the summary note. :8770 was stopped by exact command line.
