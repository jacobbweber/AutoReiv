---
id: CARD-529
title: "A Developer 'modify this tool' request loops and fails: it cannot read the tool's code, is offered tools it may not call, and the reply hides why"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-422
  - CARD-523
  - CARD-527
labels:
  - type:bug
  - area:developer
  - area:tools
  - P2
---

# [CARD-529] Developer modify-tool requests fail in Formulate

> **Status**: Ready (found in CARD-520 live test round 1, step 4, 2026-09-26 ~1:52 PM ET, serve `83b93ef5`). Does not block CARD-520: Ask Developer opened the chat, sent at once and marked the card, which is CARD-520's contract. P2 because every Observability tool escalation and Tools Studio "modify" uses this path.
> **Related**: CARD-520 (Ask Developer from Observability), CARD-422 (Tools Studio Talk), CARD-523 (tool-argument robustness and honest failures), CARD-527 (built-in tools)
> **Labels**: `type:bug`, `area:developer`, `area:tools`, `P2`

## Evidence

- Session `a9e6f3bf-dac6-4e76-bd21-0665fec9970d`, job `job_790a25892a59` (`catalog_resolve_rhe`) in Jacob's DB. Research was inserted for `missing_critical_roles:wiki` (the word "inventory" matched the wiki family). It matched 12 capabilities, including `tool.repo_file_read`, `repo_file_write` and `repo_file_rollback`.
- Formulate (`phase_86af5ab7e70c`, 10 turns in about 11 s, nemotron-3.5-lightning, about 3.5-4 K prompt tokens) called: `get_session_info`, then `repo_file_read {"directory": "/"}` (**blocked: "Tool 'repo_file_read' is not in agent allowlist - fail closed"**), then `plan_native_folder` on the repo root 6 times, `repo_file_read` again (blocked), and `plan_native_folder` on `D:\Projects\Active\AutoReiv\tools` ("directory not found"). Output fact: "Execution terminated: Detected repetitive cycle calling tools."
- The chat reply only says "Job job_790a25892a59 FAILED during Formulate: phase failed." The reason (repeated tool calls, blocked tool) is not shown.
- The Developer's native tool kit is `register_native_tool` and `plan_native_folder` only (`application/skills/native_tool_engineering.py`). Nothing returns an existing custom tool's code (`native_custom_tools` setting holds it), so "modify" has nothing to start from. The CARD-520 seed tool `c520_inventory_dump` has no code at all, which made the loop certain, but a real custom tool hits the same gap.

## Change (decide at refinement)

1. Give the Developer a read-only `read_native_tool(name)` (code, parameters, grants), or have Talk put the current code in the modify prompt; for a tool that does not exist, Talk answers "no custom tool called X" at once.
2. Research or Formulate must only offer capabilities the phase agent may call (drop `repo_file_read` for `developer`, or grant it read-only).
3. When a phase stops for a repetitive tool cycle or a policy block, the chat reply says that in plain words (for example "Stopped: the Developer kept calling plan_native_folder with the same folder").
4. Consider not routing a Tools Studio intent through catalog research on keyword families ("inventory" → wiki).

## Done when

A modify request for an existing custom tool reads its code and proposes a change; a modify request for a missing tool says it does not exist; no phase is offered a tool outside its allowlist; a cycle stop shows its reason in the chat. Replay: seed `scratch\c520_seed_serve.py`, Ask Developer on the card.
