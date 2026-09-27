---
id: CARD-550
title: "Developer ticks coding (the repo_file_* checkout tools)"
status: Done
created: 2026-09-27
branch: feat/card-550-developer-ticks-coding
related:
  - CARD-544
  - CARD-539
  - CARD-552
  - CARD-553
  - CARD-554
  - CARD-555
labels:
  - type:product
  - area:agents
  - P3
---

# [CARD-550] Developer ticks coding (the checkout repo_file_* tools)

> **Status**: Done (merged to qa on 2026-09-27 after Jacob's "merge to qa" at 12:07 PM ET, after CARD-537). It was In Review (2026-09-27 ET) on `feat/card-550-developer-ticks-coding`, from qa `44ea9201`. The card was filed as "Nobody ticks the checkout (repo_file_*) tools now" while checking the CARD-544 migration on Jacob's real data (2026-09-27 ~3:05 AM ET). D1 was decided by Jacob at 9:22 AM ET.
> **Related**: CARD-544, CARD-539; filed from live QA: CARD-552, CARD-553, CARD-554, CARD-555
> **Labels**: `type:product`, `area:agents`, `P3`

## Evidence (as filed)

After the CARD-544 migration, Jacob's live data has AutoReiv without `coding`. The Developer never ticked a skill called `coding`. Its skills are sdlc-engineering, mcp-engineering, native-tool-engineering, capability-authoring, proposals and build-agent-pack. Its 30 allowed tools include `read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec` and `execute_code`. None of them are the `coding` skill's `repo_file_read` / `repo_file_list` / `repo_file_write` / `repo_file_patch`, which work on the AutoReiv checkout. So no platform agent could read or patch the AutoReiv checkout.

## Decisions

| # | Decision | Choice | Decided |
|---|---|---|---|
| D1 | Should an agent tick `coding` (checkout read/patch) by default? | **A: tick `coding` on Developer.** Code work already routes to Developer (CARD-544 D1), and the checkout is the one codebase Developer could not reach. | Jacob, 2026-09-27 (9:22 AM ET) |

## Requirements (EARS)

- **REQ-550-001**: THE SYSTEM SHALL ship the Developer platform pack with `coding` in `allowed_skill`, a `coding` skills entry bound to `repo_file_read`, `repo_file_list`, `repo_file_write` and `repo_file_patch`, and the runbook at `platform-packs/developer/skills/coding/SKILL.md`.
- **REQ-550-002**: WHEN the app starts on data where the stored Developer profile does not tick `coding` THE SYSTEM SHALL tick it once through an idempotent migration. The migration writes a backup of the old skill list and a marker, saves through the shared skill path, and syncs pack.json. It SHALL NOT re-tick `coding` after the operator unticks it, SHALL respect an operator-disabled `coding`, and SHALL leave an agent that already ticks it unchanged.
- **REQ-550-003**: WHEN the platform update at bootstrap already gave an unedited Developer the new pack THE SYSTEM SHALL still write the backup, using the skill list read before bootstrap (`"by": "platform update"`), and set the marker.
- **REQ-550-004**: `resolve_allowed_tools(developer)` SHALL include the four `repo_file_*` tools. A code request in an AutoReiv chat that needs a checkout file SHALL reach Developer with `repo_file_read` allowed and no policy block.

## Implementation (2026-09-27)

| Commit | What |
|---|---|
| `1997fcb6` | Tests first, confirmed red. `tests/unit/agent_packs/test_card550_developer_ticks_coding.py` has 8 tests: the pack, the runbook, resolved tools, the migration (once, backup, marker, pack.json sync), bootstrap ordering, operator untick, operator disabled, already ticked, and code capabilities route to Developer. Also a guard in `tests/unit/agents/test_builtin_profiles.py` and smoke TC-38 (the Developer coding pill is pressed). |
| `cf096c4f` | `platform-packs/developer/pack.json` ticks `coding` and adds the skills entry. The runbook ships under Developer (the AutoReiv copy stays for the CARD-544 re-tick pill). `tick_developer_coding` and `developer_skills_before_seed` in `capability_migration.py` (marker `developer_coding_ticked_card550`, backup `migrations/card-550-developer-skills.json`). `src/web/app.py` captures Developer's skills before `BuiltinAgentRegistry.bootstrap` and runs the migration after CARD-544's. |
| `e5182110` | Live QA journey `tests/e2e/journeys/card-550-checkout-code-to-developer.mjs`. |
| `2398e39b`, `404efd2d`, `2ed5a62a` | Journey fixes from live QA. A handoff can start inside a job phase, and the Developer child runs in its own session (`<phase session>_child_<id>`, stored under developer). The journey reads the chat, the phase chats and the handoff child sessions. It passes when the request reaches Developer and Developer has `repo_file_read` (a successful row, or listed in the Developer session's tool list). It fails on any Developer `repo_file_*` policy block. |

The ask was changed from read-only to "read ... with the repository tools, then write and run a small snippet". With a read-only ask, AutoReiv answers by itself through the platform-wide `read_document_file` (CARD-552).

## Evidence

**Tests vs baseline**: full suite on `2ed5a62a` code (smoke run on its own):

| Suite | Result | Baseline |
|---|---|---|
| Unit | 2075 passed, 11 skipped, 1 failed (CARD-454 linter, scanned 23, 4 errors) | same failure (was 2067 passed; +8 CARD-550) |
| Integration | 103 passed | 103 |
| Vitest | 949 passed, 3 failed (CARD-456) | same 3 |
| ESLint (`src/web/static`) | 4 errors, 5 warnings | 4 + 5 |
| Ruff | 7 | 7 |
| Smoke | 73 passed | 73 |

**Live QA** (throwaway env on :8770, real vLLM; reports under `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\`):

| Journey | Desktop | Phone | Notes |
|---|---|---|---|
| card-550-checkout-code-to-developer (final, `card-550-r3`) | PASS | PASS | Desktop: 2 handoffs to Developer; Developer's `repo_file_read` succeeded (`checkout_root D:\Projects\Active\AutoReiv`); 0 Developer policy blocks. Phone: 1 handoff; the Developer session lists all four `repo_file_*` tools; 0 Developer policy blocks. AutoReiv's own `repo_file_read` attempts were blocked, as expected after CARD-544. |
| card-520-teach-needs-tool (regression, `card-550`) | PASS | PASS | 7/7 steps each, with the CARD-535 nudge as before. |
| card-550 earlier runs | FAIL | FAIL | Journey bugs (did not look in phase or handoff child sessions) plus the read-only ask. The product findings are filed below. |

**Real-data migration check**: not run on this branch, because it is not merged. The unit tests cover the stored-profile, bootstrap-ordering and operator cases.

## Findings filed as Ready cards

- **CARD-552** (P2): `read_document_file` reads any path on disk (no path guard).
- **CARD-553** (P2): a handoff from a job phase keeps the job's capability subset, so Developer's `cli_exec` and `execute_code` are skipped as "out of matched capability subset".
- **CARD-554** (P3): Formulate does the work itself, then ends FAILED after a completed handoff ("another run of this job changed this step"), and the Developer Execute phase never starts.
- **CARD-555** (P2): live QA's throwaway serve points the checkout tools at the real repo, and a stray `get_weather_tool.json` appeared during the CARD-520 run.

## Done when

- The pack, migration, guard and smoke tests pass.
- The journey passes on desktop and phone, and CARD-520 still passes.
- CHANGELOG and roadmap are updated.
- Jacob says "merge to qa".
