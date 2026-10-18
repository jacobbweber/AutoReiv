---
id: CARD-715
title: "Decompose backend monoliths over 800 lines (education.py, education_tools.py, course.py, job_phase_orchestrator.py, update_service.py, card_tools.py)"
type: feature
status: Ready
priority: P3
milestone: M31
needs_decision: none
proof:
  journeys: [card-715-backend-monolith-decomposition]
  checks: [tests/unit/architecture/test_card715_backend_file_size_guard.py]
branch: feat/card-715-backend-monolith-decomposition
log: {minutes: 0, qa_runs: 0, findings: 0}
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
- Refactor `_write_step_artifact_body()` in `src/application/education/course.py` to use a step-formatter dispatch table + shared note/mastery/fact persistence helper.
- Split `src/web/routers/education.py` (1,909L) and move raw SQL at line 360 into `education_mastery_ops.py`.
- Split `src/application/skills/education_tools.py` (1,248L) into quiz/SRS tools vs. curriculum/summary tools and schema definitions.
- Split crash/kill recovery (`checkpoint_mid_llm_kill_phase`, `resume_after_crash`) and catalog-resolve job creation out of `src/application/orchestration/job_phase_orchestrator.py` (1,180L).
- Split git CLI / branch operations vs. update scheduling / DB backup out of `src/application/system/update_service.py` (987L).
- Split markdown card formatting helpers out of `src/application/skills/card_tools.py` (824L).

## What dies
- 7-branch copy-pasted boilerplate in `course.py:_write_step_artifact_body()`.
- Raw SQL `conn.execute("UPDATE education_mastery ...")` inside `src/web/routers/education.py`.

## Proof
- Journey `card-715-backend-monolith-decomposition`:
  1. Exercise Education Studio (courses/quiz) and Settings > Updates check on desktop and phone, verifying all decomposed endpoints and tools work identically.
- Checks:
  - `tests/unit/architecture/test_card715_backend_file_size_guard.py`

## Plan and decisions
- Phase 3 backend monolith decomposition.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-715\...`

## Release note
- Decomposed `education.py`, `education_tools.py`, `course.py`, `job_phase_orchestrator.py`, `update_service.py`, and `card_tools.py` under the 800-line ceiling and enforced a Python file-size guard test [CARD-715].
