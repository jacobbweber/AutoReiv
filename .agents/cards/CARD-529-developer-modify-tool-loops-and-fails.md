---
id: CARD-529
title: "A job phase stopped by a repeat-cycle or policy block says only \"phase failed\" in chat (items 1, 2, 4 done elsewhere)"
status: Superseded
completed: 2026-09-30
created: 2026-09-26
branch: qa
related:
  - CARD-539
  - CARD-520
  - CARD-422
  - CARD-523
  - CARD-527
labels:
  - type:bug
  - area:developer
  - area:tools
  - P2
needs_decision: none
milestone: M25
---

# [CARD-529] Developer modify-tool requests fail in Formulate

> **Partly superseded (2026-09-26)** by [CARD-539](CARD-539-capability-scoping-one-allowed-tools-function.md) / [ADR-0061](../adr/0061-capability-scoping-skills-only-permission-one-enforcement-point.md): change items 2 (tools offered outside the allowlist) and 4 (keyword-family catalog routing) moved there. This card keeps items 1 and 3, which are separate concerns (Developer tooling and honest stop reasons). Build after CARD-539.

> **Status**: Superseded (closed 2026-09-30)
> **Related**: CARD-520 (Ask Developer from Observability), CARD-422 (Tools Studio Talk), CARD-523 (tool-argument robustness and honest failures), CARD-527 (built-in tools)
> **Labels**: `type:bug`, `area:developer`, `area:tools`, `P2`

## Evidence

- Session `a9e6f3bf-dac6-4e76-bd21-0665fec9970d`, job `job_790a25892a59` (`catalog_resolve_rhe`) in Jacob's DB. Research was inserted for `missing_critical_roles:wiki` (the word "inventory" matched the wiki family). It matched 12 capabilities, including `tool.repo_file_read`, `repo_file_write` and `repo_file_rollback`.
- Formulate (`phase_86af5ab7e70c`, 10 turns in about 11 s, nemotron-3.5-lightning, about 3.5-4 K prompt tokens) called: `get_session_info`, then `repo_file_read {"directory": "/"}` (**blocked: "Tool 'repo_file_read' is not in agent allowlist - fail closed"**), then `plan_native_folder` on the repo root 6 times, `repo_file_read` again (blocked), and `plan_native_folder` on `D:\Projects\Active\AutoReiv\tools` ("directory not found"). Output fact: "Execution terminated: Detected repetitive cycle calling tools."
- The chat reply only says "Job job_790a25892a59 FAILED during Formulate: phase failed." The reason (repeated tool calls, blocked tool) is not shown.
- The Developer's native tool kit is `register_native_tool` and `plan_native_folder` only (`application/skills/native_tool_engineering.py`). Nothing returns an existing custom tool's code (`native_custom_tools` setting holds it), so "modify" has nothing to start from. The CARD-520 seed tool `c520_inventory_dump` has no code at all, which made the loop certain, but a real custom tool hits the same gap.

## Change (decide at refinement)

1. Give the Developer a read-only `read_native_tool(name)` (code, parameters, which skills bind it), or have Talk put the current code in the modify prompt; for a tool that does not exist, Talk answers "no custom tool called X" at once. Per ADR-0061 the tool is bound to Developer's `native-tool-engineering` skill with a runbook line, not granted on its own.
2. *(Moved to CARD-539: no phase is offered a tool outside the agent's allowed set.)*
3. When a phase stops for a repetitive tool cycle or a policy block, the chat reply says that in plain words (for example "Stopped: the Developer kept calling plan_native_folder with the same folder").
4. *(Moved to CARD-539: catalog matching is scoped to the agent's own ticked skills.)*

## Done when

A modify request for an existing custom tool reads its code and proposes a change; a modify request for a missing tool says it does not exist; a cycle or policy stop shows its reason in the chat. Replay: seed `scratch\c520_seed_serve.py`, Ask Developer on the card, or a `scripts/live_qa.py` journey.

## Log
- 2026-09-29: Shrunk in CARD-577 to item 3 (honest stop reason); item 1 done by CARD-571 (view_native_tool).

## Closed (2026-09-30)

Closed by Jacob 2026-09-30. Items 1, 2, 4 were done elsewhere (CARD-571, CARD-539). Item 3's cause is gone: a
repeat-cycle stop now answers with a no-tools final reply (CARD-551) and a turn-limit stop with a short summary
(CARD-461), so a stopped phase no longer ends on a bare error line.
