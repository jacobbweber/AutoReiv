---
id: CARD-715
title: "Decompose backend monoliths over 800 lines (education.py, education_tools.py, course.py, job_phase_orchestrator.py, update_service.py, card_tools.py)"
type: feature
status: In Review
priority: P3
milestone: M31
needs_decision: none
proof:
  journeys: [card-715-backend-monolith-decomposition]
  checks: [tests/unit/architecture/test_card715_backend_file_size_guard.py]
branch: feat/card-715-backend-monolith-decomposition
log: {minutes: 35, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-715 Decompose backend monoliths over 800 lines (education.py, education_tools.py, course.py, job_phase_orchestrator.py, update_service.py, card_tools.py)

## Intent
Bring the remaining backend Python files that exceed the 800-line rule (`src/web/routers/education.py` [1,909L], `src/application/skills/education_tools.py` [1,248L], `src/application/orchestration/job_phase_orchestrator.py` [1,180L], `src/application/system/update_service.py` [987L], `src/application/education/course.py` [943L], and `src/application/skills/card_tools.py` [824L]) under 800 lines with clean module boundaries and zero raw SQL in routers.

## Goal
1. Every Python file under `src/` is at or below 800 lines, enforced by a fast guard test.
2. `course.py`'s 491-line `_write_step_artifact_body()` `if/elif` chain is replaced with a data-driven step renderer table and helper.
3. `src/web/routers/education.py` moves its raw `UPDATE education_mastery` SQL into `AgentMemoryRepository` and splits its 33 endpoints into sub-routers (courses/steps, quizzes/mastery, learner/delivery).
4. `education_tools.py`, `job_phase_orchestrator.py`, `update_service.py`, and `card_tools.py` are split by responsibility into cohesive modules under 800 lines.

## Change
- Refactored `_write_step_artifact_body()` out of `src/application/education/course.py` (943 -> 380L) into `src/application/education/course_step_artifacts.py` (469L) with a shared `_save_note_with_mastery_and_fact()` persistence helper.
- Split `src/web/routers/education.py` (1,909 -> 680L) into `src/web/routers/education_deps.py` (90L), `src/web/routers/education_practice.py` (645L), and `src/web/routers/education_courses.py` (395L), and moved raw `UPDATE education_mastery` SQL into `AgentMemoryRepository.force_education_mastery_due` / `schedule_education_mastery_due` in `src/infrastructure/memory/repositories/education_mastery_ops.py`.
- Split `src/application/skills/education_tools.py` (1,248 -> 640L) and `src/application/skills/education_tool_schemas.py` (611L).
- Split crash/kill recovery (`checkpoint_mid_llm_kill_phase`, `resume_after_crash`) and catalog-resolve job creation out of `src/application/orchestration/job_phase_orchestrator.py` (1,180 -> 774L) into `src/application/orchestration/job_recovery.py` (417L).
- Split git CLI / branch operations out of `src/application/system/update_service.py` (994 -> 640L) into `src/application/system/update_git_ops.py` (361L).
- Split markdown card formatting helpers out of `src/application/skills/card_tools.py` (825 -> 700L) into `src/application/skills/card_markdown_helpers.py` (149L).

## What dies
- 7-branch copy-pasted boilerplate in `course.py:_write_step_artifact_body()`.
- Raw SQL `conn.execute("UPDATE education_mastery ...")` inside `src/web/routers/education.py`, `src/application/skills/education_tools.py`, and `src/application/education/analysis.py`.

## Proof
- Journey `card-715-backend-monolith-decomposition`:
  1. Exercise Education Studio (courses/quiz) and Settings > Updates check on desktop and phone, verifying all decomposed endpoints and tools work identically.
- Checks:
  - `tests/unit/architecture/test_card715_backend_file_size_guard.py`

## Plan and decisions
- Phase 3 backend monolith decomposition.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-715-backend-monolith-decomposition` | desktop | PASS | 3/3 steps passed (`/api/education/*`, `/api/system/version` + `/api/system/updates`, Education Studio UI) |
| `card-715-backend-monolith-decomposition` | phone | PASS | 3/3 steps passed (`/api/education/*`, `/api/system/version` + `/api/system/updates`, Education Studio UI) |

Screenshots:
- `/tmp/autoreiv-qa/card-715/card-715-backend-monolith-decomposition-desktop-01-verify-decomposed-education-routers-course-maste.png`
- `/tmp/autoreiv-qa/card-715/card-715-backend-monolith-decomposition-desktop-03-open-education-studio-view-education-and-verify-.png`
- `/tmp/autoreiv-qa/card-715/card-715-backend-monolith-decomposition-phone-03-open-education-studio-view-education-and-verify-.png`

## Release note
- Decomposed `education.py`, `education_tools.py`, `course.py`, `job_phase_orchestrator.py`, `update_service.py`, and `card_tools.py` under the 800-line ceiling and enforced a Python file-size guard test [CARD-715].
