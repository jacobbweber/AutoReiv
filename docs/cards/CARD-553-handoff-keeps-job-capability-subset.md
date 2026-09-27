---
id: CARD-553
title: "A handoff from a job phase keeps the job's capability subset, so Developer cannot run code"
status: In Review
created: 2026-09-27
branch: feat/card-554-553-phase-handoff-tools
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

> **Status**: In Review on `feat/card-554-553-phase-handoff-tools` (2026-09-27 ET; filed from CARD-550 live QA). Combined with CARD-554 into one plan.
> **Related**: CARD-544, CARD-548, CARD-550
> **Labels**: `type:bug`, `area:orchestration`, `P2`

## Evidence

In a CARD-550 probe run on desktop, the ask was "read allowed_tools.py with the repository tools, then write and run a small Python snippet that counts the top-level defs". AutoReiv minted a job. Its Formulate phase handed off to Developer (`handoff_to_agent`) inside the phase chat. The Developer child ran as Developer, and `repo_file_read` succeeded (checkout root `D:\Projects\Active\AutoReiv`). Every `cli_exec` call was then skipped with "out of matched capability subset". In the final phone run, the same happened to `execute_code` (`{"skipped": true, "reason": "Tool 'execute_code' is out of matched capability subset (['export_agent_pack', 'inspect_agent_pack', ...])"}`). In that run, Developer also tried to hand off again and was refused by the depth limit (max 2), and a grandchild ran as AutoReiv and re-read the file with `read_document_file` (see CARD-552). The job's matched capability ids were chosen for the Formulate plan on AutoReiv, and the handoff kept them, so Developer's own allowed tools were cut down to that subset. Developer could read the file but could not run the snippet.

## Change

When a phase hands off to another agent, give the child that agent's allowed tools, or widen the subset with the target agent's matched capabilities. Do not reuse the parent job's subset unchanged. A unit test covers this: a handoff to Developer from an AutoReiv job phase whose subset lacks `tool.cli_exec` can still call `cli_exec`, which then goes through normal approval.

## Done when

The unit test passes. The CARD-550 journey's code ask shows a Developer `cli_exec` or `execute_code` row that is not skipped.

## Combined plan (CARD-554 + CARD-553 + CARD-548)

CARD-554 and CARD-553 were built as one plan on one branch, `feat/card-554-553-phase-handoff-tools`, because both come from the same code ask and share one journey. The branch is stacked on `feat/card-555-live-qa-sandbox-checkout` so live QA runs with the real-checkout guard; **merge it after CARD-555**. The Approve path it exercises is CARD-548, whose resume bug turned out to be what kept Developer's Execute phase from finishing, so the fix for that is on this branch too.

## Requirements (EARS)

- **REQ-554-001**: WHILE a job phase is a planning phase (Formulate), the tool gate SHALL block `handoff_to_agent` and work tools (the default high-risk set, and any tool with risk high or critical) with `policy_source` `planning_phase`, and the kernel SHALL NOT offer them to the model. Read tools stay allowed.
- **REQ-554-002**: WHEN a multi-phase job runs its planning phase, the assignment SHALL say "plan only", name the agent that runs each later phase, and say not to hand off. It SHALL NOT carry the repo "You MUST call `repo_file_read`" block (a short note lists the suggested paths for the plan instead).
- **REQ-554-003**: WHEN `handoff_to_agent` runs inside a running phase, the handoff SHALL NOT park that phase (unless the payload sets `park_on_handoff`), so the phase can still complete.
- **REQ-553-001**: WHEN an agent other than the job's owner runs a turn inside the job (a phase assigned to Developer, or a handoff child), its tools SHALL come from `resolve_allowed_tools` plus per-turn selection. The job's matched capability subset SHALL narrow only the job's owner agent. `ToolPolicyGate` stays the single enforcement point (ADR-0061); an unticked tool is still blocked by `agent_allowlist`, and the job's recorded ids are never widened.
- **REQ-548-001**: WHEN the operator approves a tool call parked in a job phase, the resumed turn SHALL run in that phase's session (`<sid>::phase::<id>`), and the phase's final reply SHALL be copied to the chat the operator sees.

## Implementation

| Change | Where |
|---|---|
| `is_planning_phase`, `planning_phase_block_reason`, `format_planning_phase_block`, `format_planning_repo_note` | `src/application/orchestration/phase_roles.py` (new) |
| `DEFAULT_HIGH_RISK_TOOLS` module constant (the former inline list) | `src/application/kernel/hitl_engine.py` |
| `evaluate(..., planning_phase=False)`: blocks after the allowlist check, before the subset check | `src/application/safety/tool_policy_gate.py` |
| `_matched_capability_ids_for_job(..., agent=)` returns None for a non-owner agent; `_is_planning_phase`; `_resolve_active_tools(planning_phase=)` drops blocked tools; both gate call sites pass `agent` and `planning_phase` | `src/application/kernel/agent_kernel.py` |
| `park=bool(payload.get("park_on_handoff", False))` (was always True; parking bumped the phase's step version, so the phase's own completion failed with "Another run of this job changed this step") | `src/application/orchestration/handoff_engine.py` |
| Planning phase gets the plan-only block instead of the repo MUST-read block; `resume_session_for_phase` and `relay_phase_reply_to_parent` in the open-job resume path (was streaming on the parent session, so after Approve Developer answered from the wrong transcript and its phase loop stopped after one tool) | `src/web/routers/chat.py` |
| Journey step 2 presses Approve until the job ends and asserts job DONE, Developer's Execute DONE, a successful Developer `repo_file_read`, a successful `execute_code` or `cli_exec`, no "out of matched capability subset" skip and no "changed this step" failure | `tests/e2e/journeys/card-550-checkout-code-to-developer.mjs` |
| 12 unit tests | `tests/unit/orchestration/test_card554_553_phase_handoff_tools.py` |

Commits: `8426282c` (tests, red), `338a012f` (fix), `7efcef08` (journey), `d297ac8a` (resume tests, red), `9712fe7a` (resume fix).

## Evidence (live QA, 2026-09-27 ET, real vLLM, throwaway serve from the sandbox worktree)

| Run | Journey | Desktop | Phone | Notes |
|---|---|---|---|---|
| card-554 (1:36 PM) | card-550 | FAIL | PASS | Job DONE both. Desktop: after Approve, Developer's phase stopped after `repo_file_write` and the reply came from the parent session: the CARD-548 resume bug |
| card-554b (1:40 PM) | card-550 | FAIL | n/a | Same resume bug reproduced; transcript confirmed the resumed turn ran on the parent session |
| card-554c (1:51 PM) | card-550 | PASS | PASS | After the resume fix: job DONE, Formulate(autoreiv) DONE, Execute(developer) DONE; Developer used `repo_file_read`, `execute_code`, `cli_exec`; 0 subset skips; reply "18 top-level def statements" |
| card-554d (2:01 PM) | card-520 | PASS | PASS | |
| card-554d (2:01 PM) | card-539 | PASS | WARN | Phone step 2 (due-review handoff to Tutor): the model searched the wiki instead of handing off. This is a plain chat turn, not a planning phase, and the same WARN shows in earlier runs (card-537-539, card-544, card-539-final*), tracked by CARD-546 |

The real-checkout guard (CARD-555) reported PASS on every run, and `git status --porcelain` of `D:\Projects\Active\AutoReiv` was clean before and after.

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-554c\card-550-checkout-code-to-developer-desktop-02-a-code-request-in-an-autoreiv-chat-finishes-form.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-554c\card-550-checkout-code-to-developer-phone-02-a-code-request-in-an-autoreiv-chat-finishes-form.png`.

Scavenger Pass: every `_matched_capability_ids_for_job` and `gate.evaluate` caller is in `agent_kernel.py` and passes the agent. `working_set_context` only shows the matched metadata. CARD-265's "never widen" still holds for the job's recorded ids; it no longer narrows a different agent's tools. `bind_specialist_same_job(park=True)` in `supervisor_specialist_pick.py` and the wiki grounding park in `chat.py` park on purpose (they wait for a specialist or for sources) and were left alone. Follow-up filed: CARD-557.
