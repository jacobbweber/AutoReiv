---
id: CARD-553
title: "A handoff from a job phase keeps the job's capability subset, so Developer cannot run code"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-544
  - CARD-550
  - CARD-548
labels:
  - type:bug
  - area:orchestration
  - P2
---

# [CARD-553] A handoff from a job phase keeps the job's capability subset

> **Status**: Ready (filed from CARD-550 live QA, 2026-09-27 ET).
> **Related**: CARD-544, CARD-548, CARD-550
> **Labels**: `type:bug`, `area:orchestration`, `P2`

## Evidence

In a CARD-550 probe run on desktop, the ask was "read allowed_tools.py with the repository tools, then write and run a small Python snippet that counts the top-level defs". AutoReiv minted a job. Its Formulate phase handed off to Developer (`handoff_to_agent`) inside the phase chat. The Developer child ran as Developer, and `repo_file_read` succeeded (checkout root `D:\Projects\Active\AutoReiv`). Every `cli_exec` call was then skipped with "out of matched capability subset". In the final phone run, the same happened to `execute_code` (`{"skipped": true, "reason": "Tool 'execute_code' is out of matched capability subset (['export_agent_pack', 'inspect_agent_pack', ...])"}`). In that run, Developer also tried to hand off again and was refused by the depth limit (max 2), and a grandchild ran as AutoReiv and re-read the file with `read_document_file` (see CARD-552). The job's matched capability ids were chosen for the Formulate plan on AutoReiv, and the handoff kept them, so Developer's own allowed tools were cut down to that subset. Developer could read the file but could not run the snippet.

## Change

When a phase hands off to another agent, give the child that agent's allowed tools, or widen the subset with the target agent's matched capabilities. Do not reuse the parent job's subset unchanged. A unit test covers this: a handoff to Developer from an AutoReiv job phase whose subset lacks `tool.cli_exec` can still call `cli_exec`, which then goes through normal approval.

## Done when

The unit test passes. The CARD-550 journey's code ask shows a Developer `cli_exec` or `execute_code` row that is not skipped.
