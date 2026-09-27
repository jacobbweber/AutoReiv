---
id: CARD-544
title: "Untick coding on AutoReiv so code work routes to Developer"
status: In Review
created: 2026-09-26
branch: feat/card-544-autoreiv-untick-coding
related:
  - CARD-539
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-544] Untick coding on AutoReiv so code work routes to Developer

> **Status**: In Review (2026-09-27 ~2:30 AM ET) on `feat/card-544-autoreiv-untick-coding`. D1 was decided by Jacob on 2026-09-26: untick `coding` on AutoReiv and route code work to Developer. The branch is not merged or pushed.
> **Related**: CARD-539 (ADR-0061), CARD-546, CARD-548, CARD-549
> **Labels**: `type:bug`, `area:agents`, `P2`

## Why

CARD-539 section 9.2 expects a code request to AutoReiv to be handed off to Developer. The seeded AutoReiv pack ticks `coding` (`repo_file_read`, `repo_file_list`, `repo_file_write`, `repo_file_patch`). Under ADR-0061 that puts code requests inside AutoReiv's domain. Live QA saw AutoReiv plan a job and ask for approval of `repo_file_write` itself instead of handing off. AutoReiv's pack prompt already says to hand shell and software-engineering work to Developer, so the tick contradicts the prompt.

## Decisions

| # | Decision | Choice | Decided |
|---|---|---|---|
| D1 | Should AutoReiv keep `coding` ticked? | **No.** Untick `coding` on AutoReiv. Code work (reading, writing or patching repo files, running code) routes to Developer with `handoff_to_agent`. | Jacob, 2026-09-26 |

## Requirements (EARS)

- **REQ-544-001**: THE SYSTEM SHALL ship the AutoReiv platform pack (`platform-packs/autoreiv/pack.json`) without `coding` in `allowed_skill`.
- **REQ-544-002**: WHEN the app starts on data where the stored AutoReiv profile still ticks `coding` THE SYSTEM SHALL untick it once through a real, idempotent migration. The migration writes a backup of the old skill list, records a marker, goes through the shared skill save path so platform promotion keeps the change, and changes nothing on a second run. The operator can tick `coding` again in Agent Studio afterwards, and later runs must not remove it.
- **REQ-544-003**: WHILE `coding` is not ticked for AutoReiv, `resolve_allowed_tools(autoreiv)` SHALL contain no `repo_file_*` tool, and the generated domain line SHALL not list Coding.
- **REQ-544-004**: WHEN AutoReiv receives a code request THE SYSTEM SHALL hand it off to Developer (`handoff_to_agent`), with no refusal text and without AutoReiv calling a `repo_file_*` tool.

## Tests (write first, confirm red)

- Unit: the shipped AutoReiv pack does not tick `coding`, and the resolver set for AutoReiv has no `repo_file_*` tool.
- Migration covers four cases:
  - A stored profile that ticks `coding` loses it, and a backup plus a marker are written.
  - A second run changes nothing.
  - A later operator re-tick survives both a restart and platform promotion.
  - A fresh install is untouched.
- Live QA, journey `card-539-out-of-domain-routing`, restored to the CARD-539 section 9.2 form:
  - Step 1: a code request to AutoReiv (for example, write and run a small Python function) produces a `handoff_to_agent` row to Developer, and the reply has no refusal text.
  - The Tutor due-review probe stays as an extra step.
  - Run on desktop and phone.

## Done when

- The pack and the stored AutoReiv profile no longer tick `coding`.
- The migration is tested.
- The restored routing journey hands the code request to Developer on desktop and phone. Model flakiness is tracked in CARD-546.
- CHANGELOG `[Unreleased]` is updated.

## Implementation (2026-09-27)

| Commit | What |
|---|---|
| `9f005ac4` | Tests first, confirmed red: the pack drops coding, migration, routing; the journey expects code to go to Developer. |
| `fe28e104` | Pack drops `coding`. `untick_autoreiv_coding` migration (backup, marker, shared save path, pack.json sync), wired in `src/web/app.py`. Studio still shows shipped runbooks as pills. The code family goes to Developer unless the agent ticks coding. |
| `64b1ea42` | Ruff back to baseline. |
| `424e53a8` | Smoke TC-38: `coding` is unticked on AutoReiv and the pill is still shown. |
| `3136927d` | Live QA fix: the catalog also matched `agent.autoreiv` (role bonus), and that self-match kept Execute on AutoReiv. |
| `052e7a29` | Live QA fix: **a job phase runs as its assigned agent** (`profile_for_phase` in `src/web/routers/chat.py`). Before this, every phase ran as the chat agent, so the Developer Execute phase hit `tool_policy_blocked` on `execute_code` and the job failed. |
| `98b51960` | Journey: checks that the Developer phase session has no `tool_policy_blocked` row. |
| `7031dd7c` | Checked on a clone of the real data: for an unedited AutoReiv, the platform seed sync drops `coding` at bootstrap, before the migration runs. The skill list read before bootstrap is now what gets backed up (`"by": "platform update"`). |

Deviation from REQ-544-004: a code request mints a standing job, not a `handoff_to_agent` call. Its Execute phase is assigned to Developer and runs as Developer, with Developer's tools. AutoReiv never calls a `repo_file_*` or `execute_code` tool. The journey accepts either path.

## Evidence

**Tests vs baseline** (full suite, final code `7031dd7c`, smoke run on its own):

| Suite | Result | Baseline |
|---|---|---|
| Unit | 2067 passed, 11 skipped, 1 failed (CARD-454 linter) | same failure |
| Integration | 103 passed | 103 |
| Vitest | 949 passed, 3 failed (CARD-456) | same 3 |
| ESLint | 4 errors, 5 warnings | 4 + 5 |
| Ruff | 7 | 7 |
| Smoke | 73 passed | 73 |

**Live QA** (real vLLM, throwaway env on :8770, run on `98b51960`; `7031dd7c` only changes the startup backup):

| Journey | Desktop | Phone |
|---|---|---|
| card-539-out-of-domain-routing | WARN: step 1 pass (Execute on Developer, waiting for approval of `execute_code`, 0 policy blocks); step 2 Tutor soft warn (CARD-546); step 3 pass | PASS: all 3 steps (Tutor handoff, delegation card) |
| card-520-teach-needs-tool (regression) | PASS, 7/7 | PASS, 7/7 |

Screenshots:
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-544\card-539-out-of-domain-routing-phone-01-a-code-request-to-autoreiv-goes-to-developer-no-.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-544\card-539-out-of-domain-routing-desktop-01-a-code-request-to-autoreiv-goes-to-developer-no-.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-544\card-539-out-of-domain-routing-phone-02-a-due-review-request-to-autoreiv-is-handed-off-t.png`

**Real data**: Jacob's live AutoReiv still ticks `coding` (serve on 8000 runs qa). On a clone of the live AppData started from this branch, `coding` was unticked and `{data}/migrations/card-544-autoreiv-skills.json` held the old 13-skill list (`"by": "platform update"`). The real data migrates on the first serve start after merge.

**Scavenger Pass**: no remaining code or pack text assumes AutoReiv codes. AutoReiv's prompt and the platform-health runbook already send shell and software work to Developer. The `coding` runbook still ships so the skill can be ticked again.

**Follow-ups**: CARD-548 (Approve on the Developer Execute phase resumes and finishes as Developer; not yet live-verified) and CARD-549 (Formulate should name the Execute agent).
