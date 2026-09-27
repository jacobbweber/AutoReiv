---
id: CARD-554
title: "Formulate does the work itself, then ends FAILED after a completed handoff; Execute stays queued"
status: Done
created: 2026-09-27
branch: qa
related:
  - CARD-549
  - CARD-551
  - CARD-550
labels:
  - type:bug
  - area:orchestration
  - P3
---

# [CARD-554] Formulate fails after a completed handoff and Execute never starts

> **Status**: Done (2026-09-27 ET). Jacob said "merge to qa" at 4:11 PM ET; merged `--no-ff` into qa from `feat/card-554-553-phase-handoff-tools`. Combined with CARD-553 into one plan.
> **Related**: CARD-549 (Formulate should name the Execute agent), CARD-551, CARD-550
> **Labels**: `type:bug`, `area:orchestration`, `P3`

## Evidence

For a code ask in an AutoReiv chat, the job's Execute phase was correctly assigned to Developer. Instead of planning, AutoReiv's Formulate phase tried to do the work itself:

- `repo_file_read` was blocked by policy (expected, since AutoReiv has no `coding`).
- Several `activate_skill` calls were refused.
- It then called `handoff_to_agent` to Developer from inside the Formulate phase.

The handoff completed, but Formulate ended FAILED on desktop. On phone it sat waiting for approval. In both runs Execute (Developer) stayed queued and never ran. In the final runs, both desktop and phone ended FAILED. The chat banner reads: "Job failed: Another run of this job changed this step while it was finishing, so it could not be recorded. The job was stopped so it does not hang". The handoff result row shows `parent_job_id=job_... child_job_id=job_...` with the same id. So the handoff child writes to the parent's job, and Formulate's own completion then loses the step-version check. The likely cause is that the child shares the job id instead of getting its own (or none).

## Change

Formulate should plan only, and must not call work tools or handoff. Also, a completed handoff inside a phase should not mark the phase FAILED. CARD-549's working-set line ("Execute runs on Developer; plan for it, do not run it") covers part of this. This card adds the phase-status fix and a unit test for it: a Formulate phase whose handoff child completes ends DONE, and Execute becomes runnable.

## Done when

The unit test passes. In three runs of the CARD-550 code ask, the Developer Execute phase starts.

## Combined plan (CARD-554 + CARD-553 + CARD-548)

CARD-554 and CARD-553 were built as one plan on one branch, `feat/card-554-553-phase-handoff-tools`, because both come from the same code ask and share one journey. The branch was built on `feat/card-555-live-qa-sandbox-checkout` so live QA ran with the real-checkout guard. After CARD-555 merged into qa (`b487fea0`), qa was merged into this branch (`9350a086`), so it now sits on qa. The Approve path it exercises is CARD-548, whose resume bug turned out to be what kept Developer's Execute phase from finishing, so the fix for that is on this branch too.

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
